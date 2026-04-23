use chrono::{DateTime, Timelike, Utc};
use futures_util::StreamExt;
use rdkafka::consumer::{CommitMode, Consumer, StreamConsumer};
use rdkafka::message::BorrowedMessage;
use rdkafka::producer::{FutureProducer, FutureRecord};
use rdkafka::ClientConfig;
use rdkafka::Message;
use serde_json::{json, Value};
use std::collections::HashMap;
use std::env;
use std::time::Duration;
use tokio_postgres::{Client, NoTls};
use uuid::Uuid;

#[derive(Clone)]
struct BarState {
    venue: String,
    canonical_symbol: String,
    bucket_start: DateTime<Utc>,
    open: f64,
    high: f64,
    low: f64,
    close: f64,
    trade_count: i64,
    last_event_ts: DateTime<Utc>,
}

fn env_or(name: &str, default: &str) -> String {
    env::var(name).unwrap_or_else(|_| default.to_string())
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

fn minute_bucket(ts: DateTime<Utc>) -> DateTime<Utc> {
    ts.with_second(0)
        .and_then(|v| v.with_nanosecond(0))
        .unwrap_or(ts)
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

fn message_payload_json(msg: &BorrowedMessage<'_>) -> Option<Value> {
    let payload = msg.payload_view::<str>()?.ok()?;
    serde_json::from_str::<Value>(payload).ok()
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

async fn persist_bar(conn: &Client, bar: &BarState) -> Result<(), tokio_postgres::Error> {
    conn.execute(
        "
        INSERT INTO ohlcv_bar (
          venue, canonical_symbol, timeframe, bucket_start,
          open, high, low, close, volume, trade_count, last_event_ts
        ) VALUES ($1,$2,'1m',$3,$4,$5,$6,$7,$8,$9,$10)
        ON CONFLICT (venue, canonical_symbol, timeframe, bucket_start)
        DO UPDATE SET
          high = GREATEST(ohlcv_bar.high, EXCLUDED.high),
          low = LEAST(ohlcv_bar.low, EXCLUDED.low),
          close = EXCLUDED.close,
          trade_count = GREATEST(COALESCE(ohlcv_bar.trade_count,0), COALESCE(EXCLUDED.trade_count,0)),
          last_event_ts = GREATEST(ohlcv_bar.last_event_ts, EXCLUDED.last_event_ts),
          updated_at = now()
        ",
        &[
            &bar.venue,
            &bar.canonical_symbol,
            &bar.bucket_start,
            &bar.open,
            &bar.high,
            &bar.low,
            &bar.close,
            &Option::<f64>::None,
            &bar.trade_count,
            &bar.last_event_ts,
        ],
    )
    .await?;
    Ok(())
}

async fn publish_bar(
    producer: &FutureProducer,
    output_topic: &str,
    bar: &BarState,
) -> Result<(), Box<dyn std::error::Error>> {
    let bar_event = json!({
        "venue": bar.venue,
        "canonical_symbol": bar.canonical_symbol,
        "timeframe": "1m",
        "bucket_start": bar.bucket_start.to_rfc3339(),
        "open": bar.open,
        "high": bar.high,
        "low": bar.low,
        "close": bar.close,
        "trade_count": bar.trade_count,
        "last_event_ts": bar.last_event_ts.to_rfc3339(),
    });
    let wrapped = build_envelope(bar_event).to_string();
    producer
        .send(
            FutureRecord::to(output_topic).key("").payload(&wrapped),
            Duration::from_secs(5),
        )
        .await
        .map_err(|(e, _)| e)?;
    Ok(())
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let service_name = "bar_aggregation";
    let brokers = env_or("KAFKA_BROKERS", "kafka:9092");
    let input_topic = env_or("BAR_INPUT_TOPIC", "normalized.quote.fx");
    let output_topic = env_or("BAR_OUTPUT_TOPIC", "bar.1m");
    let group_id = env_or("BAR_GROUP_ID", "nitra-bar-aggregation-v1");
    let db_dsn = env_or(
        "DATABASE_URL",
        "postgresql://trading:trading@timescaledb:5432/trading",
    );

    let (conn, connection) = tokio_postgres::connect(&db_dsn, NoTls).await?;
    tokio::spawn(async move {
        if let Err(e) = connection.await {
            eprintln!("postgres connection error: {e}");
        }
    });

    let consumer: StreamConsumer = ClientConfig::new()
        .set("bootstrap.servers", &brokers)
        .set("group.id", &group_id)
        .set("enable.auto.commit", "false")
        .set("auto.offset.reset", "earliest")
        .create()?;
    consumer.subscribe(&[&input_topic])?;

    let producer: FutureProducer = ClientConfig::new()
        .set("bootstrap.servers", &brokers)
        .set("message.timeout.ms", "5000")
        .create()?;

    let mut state: HashMap<(String, String), BarState> = HashMap::new();
    let mut stream = consumer.stream();

    while let Some(item) = stream.next().await {
        let msg = match item {
            Ok(m) => m,
            Err(_) => continue,
        };

        let source_topic = msg.topic().to_string();
        let source_partition = msg.partition();
        let source_offset = msg.offset();

        let Some(outer) = message_payload_json(&msg) else {
            consumer.commit_message(&msg, CommitMode::Sync)?;
            continue;
        };

        let message_id = outer
            .get("message_id")
            .and_then(|v| v.as_str())
            .and_then(|s| Uuid::parse_str(s).ok())
            .unwrap_or_else(Uuid::new_v4);

        if is_message_processed(&conn, service_name, message_id).await? {
            consumer.commit_message(&msg, CommitMode::Sync)?;
            continue;
        }

        let event = outer.get("payload").cloned().unwrap_or(Value::Null);
        let venue = event.get("venue").and_then(|v| v.as_str()).unwrap_or("");
        let symbol = event
            .get("canonical_symbol")
            .and_then(|v| v.as_str())
            .unwrap_or("");
        let mid = event.get("mid").and_then(|v| v.as_f64());

        if venue.is_empty() || symbol.is_empty() || mid.is_none() {
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
            continue;
        }

        let event_ts = parse_ts(event.get("event_ts_exchange").and_then(|v| v.as_str()));
        let bucket = minute_bucket(event_ts);
        let key = (venue.to_string(), symbol.to_string());
        let value = mid.unwrap_or(0.0);

        if let Some(current) = state.get(&key).cloned() {
            if current.bucket_start != bucket {
                persist_bar(&conn, &current).await?;
                publish_bar(&producer, &output_topic, &current).await?;
                state.insert(
                    key,
                    BarState {
                        venue: venue.to_string(),
                        canonical_symbol: symbol.to_string(),
                        bucket_start: bucket,
                        open: value,
                        high: value,
                        low: value,
                        close: value,
                        trade_count: 1,
                        last_event_ts: event_ts,
                    },
                );
            } else {
                let mut updated = current;
                updated.high = updated.high.max(value);
                updated.low = updated.low.min(value);
                updated.close = value;
                updated.trade_count += 1;
                updated.last_event_ts = event_ts;
                state.insert(key, updated);
            }
        } else {
            state.insert(
                key,
                BarState {
                    venue: venue.to_string(),
                    canonical_symbol: symbol.to_string(),
                    bucket_start: bucket,
                    open: value,
                    high: value,
                    low: value,
                    close: value,
                    trade_count: 1,
                    last_event_ts: event_ts,
                },
            );
        }

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
