use chrono::{DateTime, Duration as ChronoDuration, Utc};
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

async fn publish_gap(
    producer: &FutureProducer,
    output_topic: &str,
    venue: &str,
    symbol: &str,
    previous: DateTime<Utc>,
    current: DateTime<Utc>,
) -> Result<(), Box<dyn std::error::Error>> {
    let gap_event = json!({
        "gap_id": Uuid::new_v4().to_string(),
        "venue": venue,
        "canonical_symbol": symbol,
        "timeframe": "1m",
        "gap_start": (previous + ChronoDuration::minutes(1)).to_rfc3339(),
        "gap_end": (current - ChronoDuration::minutes(1)).to_rfc3339(),
        "detected_at": Utc::now().to_rfc3339(),
        "source": "nitra.gap-detection",
        "reason": "missing_minute_bars",
    });

    let wrapped = build_envelope(gap_event).to_string();
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
    let service_name = "gap_detection";
    let brokers = env_or("KAFKA_BROKERS", "kafka:9092");
    let input_topic = env_or("GAP_INPUT_TOPIC", "bar.1m");
    let output_topic = env_or("GAP_OUTPUT_TOPIC", "gap.events");
    let group_id = env_or("GAP_GROUP_ID", "nitra-gap-detection-v1");
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

    let mut last_bucket: HashMap<(String, String), DateTime<Utc>> = HashMap::new();
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

        let bar = outer.get("payload").cloned().unwrap_or(Value::Null);
        let venue = bar.get("venue").and_then(|v| v.as_str()).unwrap_or("");
        let symbol = bar
            .get("canonical_symbol")
            .and_then(|v| v.as_str())
            .unwrap_or("");
        let bucket_raw = bar.get("bucket_start").and_then(|v| v.as_str());

        if venue.is_empty() || symbol.is_empty() || bucket_raw.is_none() {
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

        let bucket = parse_ts(bucket_raw);
        let key = (venue.to_string(), symbol.to_string());
        if let Some(previous) = last_bucket.get(&key).copied() {
            if bucket > previous + ChronoDuration::minutes(1) {
                publish_gap(&producer, &output_topic, venue, symbol, previous, bucket).await?;
            }
        }
        last_bucket.insert(key, bucket);

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
