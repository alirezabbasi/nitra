use chrono::{DateTime, Duration as ChronoDuration, Utc};
use futures_util::StreamExt;
use rdkafka::consumer::{CommitMode, Consumer, StreamConsumer};
use rdkafka::message::BorrowedMessage;
use rdkafka::producer::{FutureProducer, FutureRecord};
use rdkafka::ClientConfig;
use rdkafka::Message;
use serde_json::{json, Value};
use std::env;
use std::time::Duration;
use tokio_postgres::{Client, NoTls};
use uuid::Uuid;

#[derive(Clone, Debug)]
struct GapEvent {
    gap_id: Uuid,
    venue: String,
    canonical_symbol: String,
    timeframe: String,
    gap_start: DateTime<Utc>,
    gap_end: DateTime<Utc>,
}

fn env_or(name: &str, default: &str) -> String {
    env::var(name).unwrap_or_else(|_| default.to_string())
}

fn env_bool_or(name: &str, default: bool) -> bool {
    env::var(name)
        .ok()
        .map(|v| {
            let norm = v.trim().to_ascii_lowercase();
            matches!(norm.as_str(), "1" | "true" | "yes" | "on")
        })
        .unwrap_or(default)
}

fn env_i64_or(name: &str, default: i64) -> i64 {
    env::var(name)
        .ok()
        .and_then(|v| v.parse::<i64>().ok())
        .unwrap_or(default)
}

fn parse_ts(raw: Option<&str>) -> Option<DateTime<Utc>> {
    let raw = raw?;
    DateTime::parse_from_rfc3339(raw)
        .map(|v| v.with_timezone(&Utc))
        .ok()
        .or_else(|| {
            DateTime::parse_from_rfc3339(&raw.replace('Z', "+00:00"))
                .map(|v| v.with_timezone(&Utc))
                .ok()
        })
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

fn parse_gap_event(payload: &Value) -> Option<GapEvent> {
    let venue = payload.get("venue")?.as_str()?.to_ascii_lowercase();
    let canonical_symbol = payload
        .get("canonical_symbol")?
        .as_str()?
        .to_ascii_uppercase();
    let timeframe = payload
        .get("timeframe")
        .and_then(|v| v.as_str())
        .unwrap_or("1m")
        .to_string();
    let gap_start = parse_ts(payload.get("gap_start")?.as_str())?;
    let gap_end = parse_ts(payload.get("gap_end")?.as_str())?;
    let gap_id = payload
        .get("gap_id")
        .and_then(|v| v.as_str())
        .and_then(|s| Uuid::parse_str(s).ok())
        .unwrap_or_else(Uuid::new_v4);

    Some(GapEvent {
        gap_id,
        venue,
        canonical_symbol,
        timeframe,
        gap_start,
        gap_end,
    })
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

async fn ensure_gap_backfill_tables(conn: &Client) -> Result<(), tokio_postgres::Error> {
    conn.batch_execute(
        "
        CREATE TABLE IF NOT EXISTS coverage_state (
          venue TEXT NOT NULL,
          canonical_symbol TEXT NOT NULL,
          timeframe TEXT NOT NULL DEFAULT '1m',
          last_bucket_start TIMESTAMPTZ NOT NULL,
          last_seen_at TIMESTAMPTZ NOT NULL,
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          PRIMARY KEY (venue, canonical_symbol, timeframe)
        );

        CREATE TABLE IF NOT EXISTS gap_log (
          gap_id UUID PRIMARY KEY,
          venue TEXT NOT NULL,
          canonical_symbol TEXT NOT NULL,
          timeframe TEXT NOT NULL DEFAULT '1m',
          gap_start TIMESTAMPTZ NOT NULL,
          gap_end TIMESTAMPTZ NOT NULL,
          detected_at TIMESTAMPTZ NOT NULL,
          resolved_at TIMESTAMPTZ,
          status TEXT NOT NULL DEFAULT 'open',
          source TEXT NOT NULL,
          reason TEXT,
          last_observed_bucket TIMESTAMPTZ,
          new_observed_bucket TIMESTAMPTZ,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          UNIQUE (venue, canonical_symbol, timeframe, gap_start, gap_end)
        );

        CREATE INDEX IF NOT EXISTS idx_gap_log_open ON gap_log (status, detected_at DESC);
        CREATE INDEX IF NOT EXISTS idx_gap_log_symbol ON gap_log (venue, canonical_symbol, timeframe, detected_at DESC);

        CREATE TABLE IF NOT EXISTS backfill_jobs (
          job_id UUID PRIMARY KEY,
          gap_id UUID,
          venue TEXT NOT NULL,
          canonical_symbol TEXT NOT NULL,
          timeframe TEXT NOT NULL DEFAULT '1m',
          range_start TIMESTAMPTZ NOT NULL,
          range_end TIMESTAMPTZ NOT NULL,
          status TEXT NOT NULL DEFAULT 'queued',
          attempt_count INT NOT NULL DEFAULT 0,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_backfill_jobs_status ON backfill_jobs (status, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_backfill_jobs_symbol ON backfill_jobs (venue, canonical_symbol, timeframe, created_at DESC);
        CREATE UNIQUE INDEX IF NOT EXISTS uq_backfill_jobs_range ON backfill_jobs (
          venue, canonical_symbol, timeframe, range_start, range_end
        );

        CREATE TABLE IF NOT EXISTS replay_audit (
          replay_id UUID PRIMARY KEY,
          source_topic TEXT NOT NULL,
          target_consumer_group TEXT NOT NULL,
          range_start TIMESTAMPTZ,
          range_end TIMESTAMPTZ,
          status TEXT NOT NULL DEFAULT 'queued',
          moved_messages BIGINT NOT NULL DEFAULT 0,
          started_at TIMESTAMPTZ NOT NULL,
          completed_at TIMESTAMPTZ,
          error TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_replay_audit_status ON replay_audit (status, started_at DESC);
        ",
    )
    .await
}

fn split_gap_into_chunks(
    gap_start: DateTime<Utc>,
    gap_end: DateTime<Utc>,
    chunk_minutes: i64,
) -> Vec<(DateTime<Utc>, DateTime<Utc>)> {
    if chunk_minutes <= 0 || gap_end < gap_start {
        return Vec::new();
    }

    let mut out = Vec::new();
    let mut cursor = gap_start;
    let chunk = ChronoDuration::minutes(chunk_minutes);

    while cursor <= gap_end {
        let candidate_end = cursor + chunk - ChronoDuration::minutes(1);
        let end = std::cmp::min(candidate_end, gap_end);
        out.push((cursor, end));
        cursor = end + ChronoDuration::minutes(1);
    }

    out
}

async fn try_symbol_lock(conn: &Client, lock_key: &str) -> Result<bool, tokio_postgres::Error> {
    let row = conn
        .query_one("SELECT pg_try_advisory_lock(hashtext($1));", &[&lock_key])
        .await?;
    let ok: bool = row.get(0);
    Ok(ok)
}

async fn release_symbol_lock(conn: &Client, lock_key: &str) -> Result<(), tokio_postgres::Error> {
    conn.execute("SELECT pg_advisory_unlock(hashtext($1));", &[&lock_key])
        .await?;
    Ok(())
}

async fn process_gap(
    conn: &Client,
    producer: &FutureProducer,
    replay_topic: &str,
    replay_target_group: &str,
    chunk_minutes: i64,
    gap: &GapEvent,
) -> Result<(), Box<dyn std::error::Error>> {
    let lock_key = format!("{}:{}:{}", gap.venue, gap.canonical_symbol, gap.timeframe);
    if !try_symbol_lock(conn, &lock_key).await? {
        eprintln!("backfill-worker symbol lock busy; skipping: {lock_key}");
        return Ok(());
    }

    let result = process_gap_locked(
        conn,
        producer,
        replay_topic,
        replay_target_group,
        chunk_minutes,
        gap,
    )
    .await;

    if let Err(err) = release_symbol_lock(conn, &lock_key).await {
        eprintln!("backfill-worker advisory unlock failed for {lock_key}: {err}");
    }

    result
}

async fn process_gap_locked(
    conn: &Client,
    producer: &FutureProducer,
    replay_topic: &str,
    replay_target_group: &str,
    chunk_minutes: i64,
    gap: &GapEvent,
) -> Result<(), Box<dyn std::error::Error>> {
    let chunks = split_gap_into_chunks(gap.gap_start, gap.gap_end, chunk_minutes);
    if chunks.is_empty() {
        return Ok(());
    }

    let source_topic = format!("raw.market.{}", gap.venue);

    for (range_start, range_end) in chunks {
        let job_id = Uuid::new_v4();
        let replay_id = Uuid::new_v4();

        let inserted = conn
            .execute(
                "
                INSERT INTO backfill_jobs (
                  job_id, gap_id, venue, canonical_symbol, timeframe,
                  range_start, range_end, status, attempt_count
                )
                VALUES ($1,$2,$3,$4,$5,$6,$7,'queued',0)
                ON CONFLICT (venue, canonical_symbol, timeframe, range_start, range_end)
                DO NOTHING
                ",
                &[
                    &job_id,
                    &gap.gap_id,
                    &gap.venue,
                    &gap.canonical_symbol,
                    &gap.timeframe,
                    &range_start,
                    &range_end,
                ],
            )
            .await?;

        if inserted == 0 {
            continue;
        }

        let replay_payload = json!({
            "replay_id": replay_id.to_string(),
            "source_topic": source_topic,
            "start_ts": range_start.to_rfc3339(),
            "end_ts": range_end.to_rfc3339(),
            "target_consumer_group": replay_target_group,
            "requested_by": "nitra-backfill-worker",
            "requested_at": Utc::now().to_rfc3339(),
            "dry_run": false,
            "fetch_mode": "broker_history",
            "venue": gap.venue,
            "canonical_symbol": gap.canonical_symbol,
            "timeframe": gap.timeframe,
            "trigger": "gap_backfill",
        });

        let wrapped = build_envelope(replay_payload).to_string();
        let key = format!("{}:{}", gap.venue, gap.canonical_symbol);
        producer
            .send(
                FutureRecord::to(replay_topic).key(&key).payload(&wrapped),
                Duration::from_secs(5),
            )
            .await
            .map_err(|(e, _)| e)?;

        conn.execute(
            "
            INSERT INTO replay_audit (
              replay_id, source_topic, target_consumer_group, range_start, range_end,
              status, moved_messages, started_at
            )
            VALUES ($1,$2,$3,$4,$5,'queued',0,now())
            ON CONFLICT (replay_id) DO NOTHING
            ",
            &[
                &replay_id,
                &source_topic,
                &replay_target_group,
                &range_start,
                &range_end,
            ],
        )
        .await?;
    }

    conn.execute(
        "
        UPDATE gap_log
        SET status='backfill_queued', updated_at=now()
        WHERE gap_id=$1 AND status='open'
        ",
        &[&gap.gap_id],
    )
    .await?;

    Ok(())
}

async fn process_open_gaps(
    conn: &Client,
    producer: &FutureProducer,
    replay_topic: &str,
    replay_target_group: &str,
    chunk_minutes: i64,
) -> Result<(), Box<dyn std::error::Error>> {
    let rows = conn
        .query(
            "
            SELECT gap_id, venue, canonical_symbol, timeframe, gap_start, gap_end
            FROM gap_log
            WHERE status = 'open'
              AND timeframe = '1m'
            ORDER BY detected_at ASC
            ",
            &[],
        )
        .await?;

    for row in rows {
        let gap = GapEvent {
            gap_id: row.get(0),
            venue: row.get::<usize, String>(1),
            canonical_symbol: row.get::<usize, String>(2),
            timeframe: row.get::<usize, String>(3),
            gap_start: row.get(4),
            gap_end: row.get(5),
        };
        process_gap(
            conn,
            producer,
            replay_topic,
            replay_target_group,
            chunk_minutes,
            &gap,
        )
        .await?;
    }

    Ok(())
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let service_name = "backfill_worker";
    let brokers = env_or("KAFKA_BROKERS", "kafka:9092");
    let input_topic = env_or("BACKFILL_INPUT_TOPIC", "gap.events");
    let output_topic = env_or("BACKFILL_REPLAY_TOPIC", "replay.commands");
    let group_id = env_or("BACKFILL_GROUP_ID", "nitra-backfill-worker-v1");
    let target_group = env_or("BACKFILL_TARGET_GROUP", "nitra-market-normalization-v1");
    let db_dsn = env_or(
        "DATABASE_URL",
        "postgresql://trading:trading@timescaledb:5432/trading",
    );

    let startup_process_open_gaps = env_bool_or("BACKFILL_STARTUP_PROCESS_OPEN_GAPS", true);
    let chunk_minutes = env_i64_or("BACKFILL_FETCH_CHUNK_MINUTES", 60).max(1);

    let (conn, connection) = tokio_postgres::connect(&db_dsn, NoTls).await?;
    tokio::spawn(async move {
        if let Err(e) = connection.await {
            eprintln!("postgres connection error: {e}");
        }
    });

    ensure_gap_backfill_tables(&conn).await?;

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

    if startup_process_open_gaps {
        process_open_gaps(
            &conn,
            &producer,
            &output_topic,
            &target_group,
            chunk_minutes,
        )
        .await?;
    }

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

        let gap_payload = outer.get("payload").cloned().unwrap_or(Value::Null);
        if let Some(gap) = parse_gap_event(&gap_payload) {
            process_gap(
                &conn,
                &producer,
                &output_topic,
                &target_group,
                chunk_minutes,
                &gap,
            )
            .await?;
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn chunking_splits_precisely() {
        let start = DateTime::parse_from_rfc3339("2026-04-18T10:00:00Z")
            .expect("start")
            .with_timezone(&Utc);
        let end = DateTime::parse_from_rfc3339("2026-04-18T10:09:00Z")
            .expect("end")
            .with_timezone(&Utc);

        let chunks = split_gap_into_chunks(start, end, 3);
        assert_eq!(chunks.len(), 4);
        assert_eq!(chunks[0].0.to_rfc3339(), "2026-04-18T10:00:00+00:00");
        assert_eq!(chunks[0].1.to_rfc3339(), "2026-04-18T10:02:00+00:00");
        assert_eq!(chunks[3].0.to_rfc3339(), "2026-04-18T10:09:00+00:00");
        assert_eq!(chunks[3].1.to_rfc3339(), "2026-04-18T10:09:00+00:00");
    }

    #[test]
    fn chunking_empty_on_inverted_range() {
        let start = DateTime::parse_from_rfc3339("2026-04-18T10:10:00Z")
            .expect("start")
            .with_timezone(&Utc);
        let end = DateTime::parse_from_rfc3339("2026-04-18T10:09:00Z")
            .expect("end")
            .with_timezone(&Utc);

        let chunks = split_gap_into_chunks(start, end, 5);
        assert!(chunks.is_empty());
    }
}
