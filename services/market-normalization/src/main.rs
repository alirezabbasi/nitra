use chrono::{DateTime, Datelike, Timelike, Utc};
use futures_util::StreamExt;
use rdkafka::consumer::{CommitMode, Consumer, StreamConsumer};
use rdkafka::message::BorrowedMessage;
use rdkafka::producer::{FutureProducer, FutureRecord};
use rdkafka::ClientConfig;
use rdkafka::Message;
use serde_json::{json, Value};
use std::collections::HashMap;
use std::env;
use std::fs;
use std::fmt::Write as _;
use std::time::Duration;
use tokio_postgres::{Client, NoTls};
use uuid::Uuid;

fn env_or(name: &str, default: &str) -> String {
    env::var(name).unwrap_or_else(|_| default.to_string())
}

fn csv_env(name: &str, default: &str) -> Vec<String> {
    env_or(name, default)
        .split(',')
        .map(|item| item.trim().to_string())
        .filter(|item| !item.is_empty())
        .collect()
}

fn canonical_symbol(broker_symbol: &str) -> String {
    broker_symbol
        .replace('_', "")
        .replace('-', "")
        .replace('.', "")
        .to_uppercase()
}

fn infer_asset_class_from_symbol(symbol: &str) -> &'static str {
    let canonical = canonical_symbol(symbol);
    if let Some(base) = canonical.strip_suffix("USD") {
        if matches!(
            base,
            "BTC"
                | "ETH"
                | "SOL"
                | "ADA"
                | "XRP"
                | "LTC"
                | "DOGE"
                | "BNB"
                | "AVAX"
                | "DOT"
                | "LINK"
        ) {
            return "crypto";
        }
    }
    "fx"
}

fn classify_market_payload(payload: &Value) -> &'static str {
    if payload.get("bid").is_some() || payload.get("ask").is_some() {
        return "raw_tick";
    }
    if payload.get("price").is_some() && payload.get("size").is_some() {
        return "trade_print";
    }
    if payload.get("best_bid").is_some() || payload.get("best_ask").is_some() {
        return "book_event";
    }
    "raw_tick"
}

fn parse_ts(value: Option<&str>) -> DateTime<Utc> {
    if let Some(raw) = value {
        if let Ok(parsed) = DateTime::parse_from_rfc3339(raw) {
            return parsed.with_timezone(&Utc);
        }
        if let Ok(parsed) = DateTime::parse_from_rfc3339(&raw.replace('Z', "+00:00")) {
            return parsed.with_timezone(&Utc);
        }
    }
    Utc::now()
}

fn sequence_to_numeric(raw: &str) -> Option<i64> {
    let mut digits = String::new();
    for ch in raw.chars().rev() {
        if ch.is_ascii_digit() {
            digits.push(ch);
            if digits.len() >= 18 {
                break;
            }
        } else if !digits.is_empty() {
            break;
        }
    }
    if digits.is_empty() {
        return None;
    }
    let rev: String = digits.chars().rev().collect();
    rev.parse::<i64>().ok()
}

fn build_envelope(payload: Value) -> Value {
    json!({
        "message_id": Uuid::new_v4().to_string(),
        "emitted_at": Utc::now().to_rfc3339(),
        "schema_version": 1,
        "headers": {},
        "payload": payload,
        "retry": Value::Null,
    })
}

fn normalize_topic_segment(topic: &str) -> String {
    topic
        .chars()
        .map(|ch| {
            if ch.is_ascii_alphanumeric() || ch == '.' || ch == '-' || ch == '_' {
                ch
            } else {
                '_'
            }
        })
        .collect()
}

fn canonical_raw_lake_object_key(
    venue: &str,
    broker_symbol: &str,
    source_topic: &str,
    source_partition: i32,
    event_ts_received: &DateTime<Utc>,
) -> String {
    let venue_part = venue.to_ascii_lowercase();
    let symbol_part = canonical_symbol(broker_symbol);
    let topic_part = normalize_topic_segment(source_topic);
    format!(
        "raw_capture/format=parquet/venue={}/topic={}/partition={}/symbol={}/year={:04}/month={:02}/day={:02}/hour={:02}/capture.parquet",
        venue_part,
        topic_part,
        source_partition,
        symbol_part,
        event_ts_received.year(),
        event_ts_received.month(),
        event_ts_received.day(),
        event_ts_received.hour()
    )
}

fn load_symbol_registry(path: &str) -> HashMap<(String, String), String> {
    let Ok(raw) = fs::read_to_string(path) else {
        return HashMap::new();
    };

    let Ok(value) = serde_json::from_str::<Value>(&raw) else {
        return HashMap::new();
    };

    let mut mapping = HashMap::new();
    let Some(rows) = value.get("mappings").and_then(|v| v.as_array()) else {
        return mapping;
    };

    for row in rows {
        let venue = row
            .get("venue")
            .and_then(|v| v.as_str())
            .unwrap_or_default()
            .to_lowercase();
        let broker_symbol = row
            .get("broker_symbol")
            .and_then(|v| v.as_str())
            .unwrap_or_default()
            .to_string();
        let canonical = row
            .get("canonical_symbol")
            .and_then(|v| v.as_str())
            .unwrap_or_default()
            .to_string();

        if !venue.is_empty() && !broker_symbol.is_empty() && !canonical.is_empty() {
            mapping.insert((venue, broker_symbol), canonical);
        }
    }

    mapping
}

fn canonical_from_registry_or_fallback(
    registry: &HashMap<(String, String), String>,
    venue: &str,
    broker_symbol: &str,
) -> String {
    if let Some(found) = registry.get(&(venue.to_lowercase(), broker_symbol.to_string())) {
        return found.clone();
    }
    canonical_symbol(broker_symbol)
}

async fn is_message_processed(
    conn: &Client,
    service_name: &str,
    message_id: Uuid,
) -> Result<bool, tokio_postgres::Error> {
    let row = conn
        .query_opt(
            "
            SELECT 1
            FROM processed_message_ledger
            WHERE service_name = $1 AND message_id = $2::uuid
            ",
            &[&service_name, &message_id],
        )
        .await?;
    Ok(row.is_some())
}

async fn record_message_processed(
    conn: &Client,
    service_name: &str,
    message_id: Uuid,
    source_topic: &str,
    source_partition: i32,
    source_offset: i64,
) -> Result<(), tokio_postgres::Error> {
    conn.execute(
        "
        INSERT INTO processed_message_ledger (
          service_name, message_id, source_topic, source_partition, source_offset
        ) VALUES ($1, $2::uuid, $3, $4, $5)
        ON CONFLICT DO NOTHING
        ",
        &[
            &service_name,
            &message_id,
            &source_topic,
            &source_partition,
            &source_offset,
        ],
    )
    .await?;
    Ok(())
}

async fn persist_market_entity(
    conn: &Client,
    entity_type: &str,
    message_id: Uuid,
    raw_event: &Value,
) -> Result<(), tokio_postgres::Error> {
    let venue = raw_event
        .get("venue")
        .and_then(|v| v.as_str())
        .unwrap_or("unknown");
    let broker_symbol = raw_event
        .get("broker_symbol")
        .and_then(|v| v.as_str())
        .unwrap_or("UNKNOWN");
    let event_ts_received = parse_ts(raw_event.get("event_ts_received").and_then(|v| v.as_str()));
    let source = raw_event
        .get("source")
        .and_then(|v| v.as_str())
        .unwrap_or("nitra.market_normalization");
    let payload = raw_event.get("payload").unwrap_or(&Value::Null);
    let event_ts_exchange = parse_ts(payload.get("event_ts_exchange").and_then(|v| v.as_str()));
    let sequence_id = payload
        .get("sequence_id")
        .and_then(|v| v.as_str())
        .map(|v| v.to_string());

    let payload_json = payload.clone();

    if entity_type == "trade_print" {
        conn.execute(
            "
            INSERT INTO trade_print (
              message_id, venue, broker_symbol, event_ts_exchange, event_ts_received,
              source, price, size, side, sequence_id, payload
            ) VALUES ($1::uuid,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11::jsonb)
            ON CONFLICT (message_id, event_ts_received) DO NOTHING
            ",
            &[
                &message_id,
                &venue,
                &broker_symbol,
                &event_ts_exchange,
                &event_ts_received,
                &source,
                &payload.get("price").and_then(|v| v.as_f64()),
                &payload.get("size").and_then(|v| v.as_f64()),
                &payload.get("side").and_then(|v| v.as_str()),
                &sequence_id,
                &payload_json,
            ],
        )
        .await?;
    } else if entity_type == "book_event" {
        conn.execute(
            "
            INSERT INTO book_event (
              message_id, venue, broker_symbol, event_ts_exchange, event_ts_received,
              source, best_bid, best_ask, sequence_id, payload
            ) VALUES ($1::uuid,$2,$3,$4,$5,$6,$7,$8,$9,$10::jsonb)
            ON CONFLICT (message_id, event_ts_received) DO NOTHING
            ",
            &[
                &message_id,
                &venue,
                &broker_symbol,
                &event_ts_exchange,
                &event_ts_received,
                &source,
                &payload.get("best_bid").and_then(|v| v.as_f64()),
                &payload.get("best_ask").and_then(|v| v.as_f64()),
                &sequence_id,
                &payload_json,
            ],
        )
        .await?;
    } else {
        conn.execute(
            "
            INSERT INTO raw_tick (
              message_id, venue, broker_symbol, event_ts_exchange, event_ts_received,
              source, bid, ask, mid, last, sequence_id, payload
            ) VALUES ($1::uuid,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12::jsonb)
            ON CONFLICT (message_id, event_ts_received) DO NOTHING
            ",
            &[
                &message_id,
                &venue,
                &broker_symbol,
                &event_ts_exchange,
                &event_ts_received,
                &source,
                &payload.get("bid").and_then(|v| v.as_f64()),
                &payload.get("ask").and_then(|v| v.as_f64()),
                &payload.get("mid").and_then(|v| v.as_f64()),
                &payload.get("last").and_then(|v| v.as_f64()),
                &sequence_id,
                &payload_json,
            ],
        )
        .await?;
    }

    Ok(())
}

async fn ensure_raw_capture_tables(conn: &Client) -> Result<(), tokio_postgres::Error> {
    conn.execute(
        "
        CREATE TABLE IF NOT EXISTS raw_message_capture (
          capture_id UUID PRIMARY KEY,
          message_id UUID NOT NULL,
          service_name TEXT NOT NULL,
          source_topic TEXT NOT NULL,
          source_partition INTEGER NOT NULL,
          source_offset BIGINT NOT NULL,
          venue TEXT NOT NULL,
          broker_symbol TEXT NOT NULL,
          event_ts_received TIMESTAMPTZ NOT NULL,
          sequence_id TEXT,
          sequence_numeric BIGINT,
          previous_sequence_numeric BIGINT,
          sequence_gap BIGINT,
          sequence_status TEXT NOT NULL,
          raw_message_text TEXT NOT NULL,
          raw_message_json JSONB NOT NULL,
          raw_payload_json JSONB NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          UNIQUE (source_topic, source_partition, source_offset)
        )
        ",
        &[],
    )
    .await?;
    conn.execute(
        "
        CREATE INDEX IF NOT EXISTS idx_raw_message_capture_symbol_ts
          ON raw_message_capture (venue, broker_symbol, created_at DESC)
        ",
        &[],
    )
    .await?;
    conn.execute(
        "
        CREATE INDEX IF NOT EXISTS idx_raw_message_capture_sequence_status
          ON raw_message_capture (sequence_status, created_at DESC)
        ",
        &[],
    )
    .await?;
    Ok(())
}

async fn ensure_raw_lake_manifest_table(conn: &Client) -> Result<(), tokio_postgres::Error> {
    conn.execute(
        "
        CREATE TABLE IF NOT EXISTS raw_lake_object_manifest (
          object_key TEXT PRIMARY KEY,
          format TEXT NOT NULL,
          venue TEXT NOT NULL,
          broker_symbol TEXT NOT NULL,
          source_topic TEXT NOT NULL,
          source_partition INTEGER NOT NULL,
          partition_year INTEGER NOT NULL,
          partition_month INTEGER NOT NULL,
          partition_day INTEGER NOT NULL,
          partition_hour INTEGER NOT NULL,
          first_event_ts_received TIMESTAMPTZ NOT NULL,
          last_event_ts_received TIMESTAMPTZ NOT NULL,
          min_source_offset BIGINT NOT NULL,
          max_source_offset BIGINT NOT NULL,
          row_count BIGINT NOT NULL DEFAULT 0,
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        ",
        &[],
    )
    .await?;
    conn.execute(
        "
        CREATE INDEX IF NOT EXISTS idx_raw_lake_manifest_partition
          ON raw_lake_object_manifest (venue, source_topic, source_partition, partition_year, partition_month, partition_day, partition_hour)
        ",
        &[],
    )
    .await?;
    Ok(())
}

async fn persist_raw_message_capture(
    conn: &Client,
    service_name: &str,
    source_topic: &str,
    source_partition: i32,
    source_offset: i64,
    message_id: Uuid,
    outer_raw: &str,
    outer: &Value,
    raw_event: &Value,
) -> Result<(), tokio_postgres::Error> {
    let venue = raw_event
        .get("venue")
        .and_then(|v| v.as_str())
        .unwrap_or("unknown");
    let broker_symbol = raw_event
        .get("broker_symbol")
        .and_then(|v| v.as_str())
        .unwrap_or("UNKNOWN");
    let payload = raw_event.get("payload").cloned().unwrap_or(Value::Null);
    let event_ts_received = parse_ts(raw_event.get("event_ts_received").and_then(|v| v.as_str()));
    let sequence_id = payload
        .get("sequence_id")
        .and_then(|v| v.as_str())
        .map(|v| v.to_string());
    let sequence_numeric = sequence_id
        .as_deref()
        .and_then(sequence_to_numeric);

    let previous_sequence_numeric: Option<i64> = conn
        .query_opt(
            "
            SELECT sequence_numeric
            FROM raw_message_capture
            WHERE venue = $1
              AND broker_symbol = $2
              AND sequence_numeric IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 1
            ",
            &[&venue, &broker_symbol],
        )
        .await?
        .and_then(|row| row.get::<usize, Option<i64>>(0));

    let (sequence_gap, sequence_status) = match (sequence_numeric, previous_sequence_numeric) {
        (Some(curr), Some(prev)) if curr == prev => (Some(0), "duplicate"),
        (Some(curr), Some(prev)) if curr < prev => (Some(prev - curr), "out_of_order"),
        (Some(curr), Some(prev)) if curr - prev > 1 => (Some(curr - prev - 1), "gap"),
        (Some(_), Some(_)) => (Some(0), "ok"),
        (Some(_), None) => (None, "initial"),
        _ => (None, "unavailable"),
    };

    conn.execute(
        "
        INSERT INTO raw_message_capture (
          capture_id, message_id, service_name, source_topic, source_partition, source_offset,
          venue, broker_symbol, event_ts_received, sequence_id, sequence_numeric,
          previous_sequence_numeric, sequence_gap, sequence_status,
          raw_message_text, raw_message_json, raw_payload_json
        ) VALUES (
          $1::uuid, $2::uuid, $3, $4, $5, $6, $7, $8, $9, $10, $11,
          $12, $13, $14, $15, $16::jsonb, $17::jsonb
        )
        ON CONFLICT (source_topic, source_partition, source_offset) DO NOTHING
        ",
        &[
            &Uuid::new_v4(),
            &message_id,
            &service_name,
            &source_topic,
            &source_partition,
            &source_offset,
            &venue,
            &broker_symbol,
            &event_ts_received,
            &sequence_id,
            &sequence_numeric,
            &previous_sequence_numeric,
            &sequence_gap,
            &sequence_status,
            &outer_raw,
            &outer.clone(),
            &payload,
        ],
    )
    .await?;

    Ok(())
}

async fn persist_raw_lake_manifest_projection(
    conn: &Client,
    source_topic: &str,
    source_partition: i32,
    source_offset: i64,
    raw_event: &Value,
) -> Result<(), tokio_postgres::Error> {
    let venue = raw_event
        .get("venue")
        .and_then(|v| v.as_str())
        .unwrap_or("unknown");
    let broker_symbol = raw_event
        .get("broker_symbol")
        .and_then(|v| v.as_str())
        .unwrap_or("UNKNOWN");
    let event_ts_received = parse_ts(raw_event.get("event_ts_received").and_then(|v| v.as_str()));
    let object_key = canonical_raw_lake_object_key(
        venue,
        broker_symbol,
        source_topic,
        source_partition,
        &event_ts_received,
    );
    let mut format = String::new();
    let _ = write!(&mut format, "parquet");
    conn.execute(
        "
        INSERT INTO raw_lake_object_manifest (
          object_key, format, venue, broker_symbol, source_topic, source_partition,
          partition_year, partition_month, partition_day, partition_hour,
          first_event_ts_received, last_event_ts_received,
          min_source_offset, max_source_offset, row_count, updated_at
        ) VALUES (
          $1, $2, $3, $4, $5, $6,
          $7, $8, $9, $10,
          $11, $11,
          $12, $12, 1, now()
        )
        ON CONFLICT (object_key) DO UPDATE
        SET first_event_ts_received = LEAST(raw_lake_object_manifest.first_event_ts_received, EXCLUDED.first_event_ts_received),
            last_event_ts_received = GREATEST(raw_lake_object_manifest.last_event_ts_received, EXCLUDED.last_event_ts_received),
            min_source_offset = LEAST(raw_lake_object_manifest.min_source_offset, EXCLUDED.min_source_offset),
            max_source_offset = GREATEST(raw_lake_object_manifest.max_source_offset, EXCLUDED.max_source_offset),
            row_count = raw_lake_object_manifest.row_count + 1,
            updated_at = now()
        ",
        &[
            &object_key,
            &format,
            &venue,
            &broker_symbol,
            &source_topic,
            &source_partition,
            &(event_ts_received.year() as i32),
            &(event_ts_received.month() as i32),
            &(event_ts_received.day() as i32),
            &(event_ts_received.hour() as i32),
            &event_ts_received,
            &source_offset,
        ],
    )
    .await?;
    Ok(())
}

async fn publish_normalized(
    producer: &FutureProducer,
    output_topic: &str,
    raw_event: &Value,
    registry: &HashMap<(String, String), String>,
) -> Result<(), Box<dyn std::error::Error>> {
    let payload = raw_event.get("payload").unwrap_or(&Value::Null);

    let bid = payload.get("bid").and_then(|v| v.as_f64());
    let ask = payload.get("ask").and_then(|v| v.as_f64());
    let mid = payload
        .get("mid")
        .and_then(|v| v.as_f64())
        .or_else(|| match (bid, ask) {
            (Some(b), Some(a)) => Some((b + a) / 2.0),
            _ => None,
        });

    let venue = raw_event
        .get("venue")
        .and_then(|v| v.as_str())
        .unwrap_or("unknown");
    let broker_symbol = raw_event
        .get("broker_symbol")
        .and_then(|v| v.as_str())
        .unwrap_or("UNKNOWN");
    let canonical = canonical_from_registry_or_fallback(registry, venue, broker_symbol);

    let normalized = json!({
        "event_id": Uuid::new_v4().to_string(),
        "venue": venue,
        "asset_class": infer_asset_class_from_symbol(&canonical),
        "broker_symbol": broker_symbol,
        "canonical_symbol": canonical,
        "event_type": "quote",
        "event_ts_exchange": payload.get("event_ts_exchange").and_then(|v| v.as_str()).unwrap_or(&Utc::now().to_rfc3339()),
        "event_ts_received": raw_event.get("event_ts_received").and_then(|v| v.as_str()).unwrap_or(&Utc::now().to_rfc3339()),
        "bid": bid,
        "ask": ask,
        "mid": mid,
        "last": payload.get("last").and_then(|v| v.as_f64()),
        "volume": payload.get("size").and_then(|v| v.as_f64()),
        "sequence_id": payload.get("sequence_id").and_then(|v| v.as_str()),
        "source_checksum": "n/a",
        "ingestion_run_id": "dev-local",
        "schema_version": 1,
    });

    let wrapped = build_envelope(normalized).to_string();
    producer
        .send(
            FutureRecord::to(output_topic).key("").payload(&wrapped),
            Duration::from_secs(5),
        )
        .await
        .map_err(|(e, _)| e)?;

    Ok(())
}

fn message_payload_json(msg: &BorrowedMessage<'_>) -> Option<(String, Value)> {
    let payload = msg.payload_view::<str>()?.ok()?;
    let value = serde_json::from_str::<Value>(payload).ok()?;
    Some((payload.to_string(), value))
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let service_name = "market_normalization";
    let brokers = env_or("KAFKA_BROKERS", "kafka:9092");
    let input_topics = csv_env(
        "NORMALIZER_INPUT_TOPICS",
        "raw.market.oanda,raw.market.capital,raw.market.coinbase",
    );
    let output_topic = env_or("NORMALIZER_OUTPUT_TOPIC", "normalized.quote.fx");
    let group_id = env_or("NORMALIZER_GROUP_ID", "nitra-market-normalization-v1");
    let db_dsn = env_or(
        "DATABASE_URL",
        "postgresql://trading:trading@timescaledb:5432/trading",
    );
    let registry_path = env_or(
        "NORMALIZER_SYMBOL_REGISTRY_PATH",
        "/etc/nitra/registry.v1.json",
    );

    let registry = load_symbol_registry(&registry_path);

    let (conn, connection) = tokio_postgres::connect(&db_dsn, NoTls).await?;
    tokio::spawn(async move {
        if let Err(e) = connection.await {
            eprintln!("postgres connection error: {e}");
        }
    });
    ensure_raw_capture_tables(&conn).await?;
    ensure_raw_lake_manifest_table(&conn).await?;

    let consumer: StreamConsumer = ClientConfig::new()
        .set("bootstrap.servers", &brokers)
        .set("group.id", &group_id)
        .set("enable.auto.commit", "false")
        .set("auto.offset.reset", "earliest")
        .create()?;

    let topic_refs: Vec<&str> = input_topics.iter().map(|v| v.as_str()).collect();
    consumer.subscribe(&topic_refs)?;

    let producer: FutureProducer = ClientConfig::new()
        .set("bootstrap.servers", &brokers)
        .set("message.timeout.ms", "5000")
        .create()?;

    let mut stream = consumer.stream();

    while let Some(item) = stream.next().await {
        let msg = match item {
            Ok(m) => m,
            Err(_) => {
                continue;
            }
        };

        let source_topic = msg.topic().to_string();
        let source_partition = msg.partition();
        let source_offset = msg.offset();

        let Some((outer_raw, outer)) = message_payload_json(&msg) else {
            consumer.commit_message(&msg, CommitMode::Sync)?;
            continue;
        };

        let raw_event = outer.get("payload").cloned().unwrap_or(Value::Null);
        if !raw_event.is_object() {
            consumer.commit_message(&msg, CommitMode::Sync)?;
            continue;
        }

        let message_id = outer
            .get("message_id")
            .and_then(|v| v.as_str())
            .and_then(|s| Uuid::parse_str(s).ok())
            .unwrap_or_else(Uuid::new_v4);

        if is_message_processed(&conn, service_name, message_id).await? {
            consumer.commit_message(&msg, CommitMode::Sync)?;
            continue;
        }

        let market_payload = raw_event.get("payload").cloned().unwrap_or(Value::Null);
        let entity_type = classify_market_payload(&market_payload);

        persist_market_entity(&conn, entity_type, message_id, &raw_event).await?;
        persist_raw_message_capture(
            &conn,
            service_name,
            &source_topic,
            source_partition,
            source_offset,
            message_id,
            &outer_raw,
            &outer,
            &raw_event,
        )
        .await?;
        persist_raw_lake_manifest_projection(
            &conn,
            &source_topic,
            source_partition,
            source_offset,
            &raw_event,
        )
        .await?;
        publish_normalized(&producer, &output_topic, &raw_event, &registry).await?;
        record_message_processed(
            &conn,
            service_name,
            message_id,
            &source_topic,
            source_partition,
            source_offset,
        )
        .await?;

        consumer.commit_message(&msg, CommitMode::Sync)?;
    }

    Ok(())
}
