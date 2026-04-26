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
use tokio::time::{interval, MissedTickBehavior};
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

fn env_u64_or(name: &str, default: u64) -> u64 {
    env::var(name)
        .ok()
        .and_then(|v| v.parse::<u64>().ok())
        .unwrap_or(default)
}

fn env_usize_or(name: &str, default: usize) -> usize {
    env::var(name)
        .ok()
        .and_then(|v| v.parse::<usize>().ok())
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
          enqueue_count INT NOT NULL DEFAULT 0,
          last_enqueued_at TIMESTAMPTZ,
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

        ALTER TABLE backfill_jobs
          ADD COLUMN IF NOT EXISTS enqueue_count INT NOT NULL DEFAULT 0;

        ALTER TABLE backfill_jobs
          ADD COLUMN IF NOT EXISTS last_enqueued_at TIMESTAMPTZ;
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
        let replay_id = job_id;

        let inserted = conn
            .execute(
                "
                INSERT INTO backfill_jobs (
                  job_id, gap_id, venue, canonical_symbol, timeframe,
                  range_start, range_end, status, attempt_count, enqueue_count, last_enqueued_at
                )
                VALUES ($1,$2,$3,$4,$5,$6,$7,'queued',0,1,now())
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

async fn reset_stale_running_jobs(
    conn: &Client,
    stale_running_secs: i64,
) -> Result<u64, tokio_postgres::Error> {
    if stale_running_secs <= 0 {
        return Ok(0);
    }
    let stale_secs_i32 = (stale_running_secs.min(i32::MAX as i64)) as i32;
    conn.execute(
        "
        UPDATE backfill_jobs
        SET status = 'queued',
            updated_at = now()
        WHERE status = 'running'
          AND updated_at < now() - ($1::int * interval '1 second')
        ",
        &[&stale_secs_i32],
    )
    .await
}

async fn requeue_stale_failed_no_source_data_jobs(
    conn: &Client,
    retry_after_secs: i64,
    max_attempts: i64,
    batch_size: i64,
) -> Result<u64, tokio_postgres::Error> {
    if retry_after_secs <= 0 || max_attempts <= 0 || batch_size <= 0 {
        return Ok(0);
    }
    let retry_after_i32 = (retry_after_secs.min(i32::MAX as i64)) as i32;
    let max_attempts_i32 = (max_attempts.min(i32::MAX as i64)) as i32;
    let batch_size_i64 = batch_size.max(1);
    let rows = conn
        .query(
            "
            WITH candidates AS (
              SELECT job_id
              FROM backfill_jobs
              WHERE status = 'failed_no_source_data'
                AND timeframe = '1m'
                AND updated_at < now() - ($1::int * interval '1 second')
                AND attempt_count < $2::int
              ORDER BY updated_at ASC
              LIMIT $3
            )
            UPDATE backfill_jobs bj
            SET status = 'queued',
                updated_at = now()
            FROM candidates c
            WHERE bj.job_id = c.job_id
            RETURNING bj.job_id
            ",
            &[&retry_after_i32, &max_attempts_i32, &batch_size_i64],
        )
        .await?;
    Ok(rows.len() as u64)
}

async fn replay_queued_count(conn: &Client) -> Result<i64, tokio_postgres::Error> {
    let row = conn
        .query_one(
            "
            SELECT COUNT(*)::bigint
            FROM replay_audit
            WHERE status = 'queued'
            ",
            &[],
        )
        .await?;
    Ok(row.get(0))
}

fn dynamic_reenqueue_batch(
    base_batch: i64,
    replay_queued: i64,
    low_watermark: i64,
    high_watermark: i64,
    min_batch: i64,
) -> i64 {
    if base_batch <= 0 {
        return 0;
    }
    if high_watermark <= 0 || replay_queued <= low_watermark {
        return base_batch;
    }
    if replay_queued >= high_watermark {
        return 0;
    }

    let min_batch = min_batch.clamp(0, base_batch);
    if high_watermark <= low_watermark {
        return min_batch;
    }

    let span = (high_watermark - low_watermark) as f64;
    let remaining = (high_watermark - replay_queued).max(0) as f64;
    let ratio = (remaining / span).clamp(0.0, 1.0);
    let scaled = (min_batch as f64) + ((base_batch - min_batch) as f64 * ratio);
    scaled.round() as i64
}

#[derive(Debug)]
struct QueuedJob {
    job_id: Uuid,
    venue: String,
    canonical_symbol: String,
    timeframe: String,
    range_start: DateTime<Utc>,
    range_end: DateTime<Utc>,
}

async fn reenqueue_queued_jobs(
    conn: &Client,
    producer: &FutureProducer,
    replay_topic: &str,
    replay_target_group: &str,
    batch_size: i64,
    queued_stale_secs: i64,
    cooldown_secs: i64,
) -> Result<u64, Box<dyn std::error::Error>> {
    if batch_size <= 0 {
        return Ok(0);
    }
    let queued_stale_secs_i32 = (queued_stale_secs.max(1).min(i32::MAX as i64)) as i32;
    let cooldown_secs_i32 = (cooldown_secs.max(0).min(i32::MAX as i64)) as i32;
    let batch_size_i64 = batch_size.max(1);
    let rows = conn
        .query(
            "
            SELECT
              bj.job_id, bj.venue, bj.canonical_symbol, bj.timeframe, bj.range_start, bj.range_end
            FROM backfill_jobs bj
            LEFT JOIN replay_audit ra ON ra.replay_id = bj.job_id
            WHERE bj.status = 'queued'
              AND bj.timeframe = '1m'
              AND (
                (
                  bj.enqueue_count = 0
                  AND bj.created_at < now() - ($1::int * interval '1 second')
                )
                OR (
                  bj.enqueue_count > 0
                  AND bj.last_enqueued_at IS NOT NULL
                  AND bj.last_enqueued_at < now() - ($2::int * interval '1 second')
                  AND (
                    ra.replay_id IS NULL
                    OR (
                      ra.status = 'queued'
                      AND ra.started_at < now() - ($1::int * interval '1 second')
                    )
                    OR (
                      ra.status = 'running'
                      AND ra.started_at < now() - ($1::int * interval '1 second')
                    )
                  )
                )
              )
            ORDER BY COALESCE(bj.last_enqueued_at, bj.created_at) ASC, bj.created_at ASC
            LIMIT $3
            ",
            &[&queued_stale_secs_i32, &cooldown_secs_i32, &batch_size_i64],
        )
        .await?;

    let mut queued_jobs = Vec::with_capacity(rows.len());
    for row in rows {
        queued_jobs.push(QueuedJob {
            job_id: row.get(0),
            venue: row.get::<usize, String>(1),
            canonical_symbol: row.get::<usize, String>(2),
            timeframe: row.get::<usize, String>(3),
            range_start: row.get(4),
            range_end: row.get(5),
        });
    }

    let mut enqueued = 0_u64;
    for job in queued_jobs {
        let source_topic = format!("raw.market.{}", job.venue);
        let replay_payload = json!({
            "replay_id": job.job_id.to_string(),
            "source_topic": source_topic,
            "start_ts": job.range_start.to_rfc3339(),
            "end_ts": job.range_end.to_rfc3339(),
            "target_consumer_group": replay_target_group,
            "requested_by": "nitra-backfill-worker-recovery",
            "requested_at": Utc::now().to_rfc3339(),
            "dry_run": false,
            "fetch_mode": "broker_history",
            "venue": job.venue,
            "canonical_symbol": job.canonical_symbol,
            "timeframe": job.timeframe,
            "trigger": "queued_recovery",
            "job_id": job.job_id.to_string(),
        });
        let wrapped = build_envelope(replay_payload).to_string();
        let key = format!("recover:{}", job.job_id);
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
              status, moved_messages, started_at, completed_at, error
            )
            VALUES ($1,$2,$3,$4,$5,'queued',0,now(),NULL,NULL)
            ON CONFLICT (replay_id)
            DO UPDATE SET
              status = 'queued',
              started_at = now(),
              completed_at = NULL,
              error = NULL,
              moved_messages = 0
            ",
            &[
                &job.job_id,
                &source_topic,
                &replay_target_group,
                &job.range_start,
                &job.range_end,
            ],
        )
        .await?;

        conn.execute(
            "
            UPDATE backfill_jobs
            SET enqueue_count = enqueue_count + 1,
                last_enqueued_at = now(),
                updated_at = now()
            WHERE job_id = $1
            ",
            &[&job.job_id],
        )
        .await?;
        enqueued += 1;
    }

    Ok(enqueued)
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
    let chunk_minutes = env_i64_or("BACKFILL_FETCH_CHUNK_MINUTES", 1440).max(1);
    let recovery_enabled = env_bool_or("BACKFILL_RECOVERY_ENABLED", true);
    let recovery_interval_secs = env_u64_or("BACKFILL_RECOVERY_INTERVAL_SECS", 60).max(10);
    let recovery_batch_size = env_usize_or("BACKFILL_RECOVERY_BATCH_SIZE", 500).max(1) as i64;
    let stale_running_secs = env_i64_or("BACKFILL_STALE_RUNNING_SECS", 900).max(1);
    let queued_stale_secs = env_i64_or("BACKFILL_QUEUED_STALE_SECS", 1800).max(1);
    let reenqueue_cooldown_secs = env_i64_or("BACKFILL_REENQUEUE_COOLDOWN_SECS", 120).max(0);
    let failed_retry_enabled = env_bool_or("BACKFILL_FAILED_RETRY_ENABLED", true);
    let failed_retry_after_secs = env_i64_or("BACKFILL_FAILED_RETRY_AFTER_SECS", 21600).max(60);
    let failed_retry_max_attempts = env_i64_or("BACKFILL_FAILED_RETRY_MAX_ATTEMPTS", 6).max(1);
    let failed_retry_batch_size =
        env_usize_or("BACKFILL_FAILED_RETRY_BATCH_SIZE", 250).max(1) as i64;
    let queue_backpressure_enabled = env_bool_or("BACKFILL_REPLAY_QUEUE_BACKPRESSURE_ENABLED", true);
    let queue_backpressure_high =
        env_i64_or("BACKFILL_REPLAY_QUEUE_HIGH_WATERMARK", 120000).max(1);
    let queue_backpressure_low = env_i64_or("BACKFILL_REPLAY_QUEUE_LOW_WATERMARK", 90000).max(0);
    let queue_backpressure_min_batch =
        env_i64_or("BACKFILL_REPLAY_QUEUE_MIN_BATCH", 100).max(0);

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

    if recovery_enabled {
        let reset = reset_stale_running_jobs(&conn, stale_running_secs).await?;
        let failed_requeued = if failed_retry_enabled {
            requeue_stale_failed_no_source_data_jobs(
                &conn,
                failed_retry_after_secs,
                failed_retry_max_attempts,
                failed_retry_batch_size,
            )
            .await?
        } else {
            0
        };
        let replay_queued = replay_queued_count(&conn).await?;
        let effective_recovery_batch = if queue_backpressure_enabled {
            dynamic_reenqueue_batch(
                recovery_batch_size,
                replay_queued,
                queue_backpressure_low,
                queue_backpressure_high,
                queue_backpressure_min_batch,
            )
        } else {
            recovery_batch_size
        };
        let enqueued = reenqueue_queued_jobs(
            &conn,
            &producer,
            &output_topic,
            &target_group,
            effective_recovery_batch,
            queued_stale_secs,
            reenqueue_cooldown_secs,
        )
        .await?;
        if reset > 0
            || failed_requeued > 0
            || enqueued > 0
            || (queue_backpressure_enabled && effective_recovery_batch != recovery_batch_size)
        {
            eprintln!(
                "backfill-worker startup recovery replay_queued={} recovery_batch={} reset_running={} failed_requeued={} re_enqueued={}",
                replay_queued, effective_recovery_batch, reset, failed_requeued, enqueued
            );
        }
    }

    let mut stream = consumer.stream();
    let mut recovery_ticker = interval(Duration::from_secs(recovery_interval_secs));
    recovery_ticker.set_missed_tick_behavior(MissedTickBehavior::Skip);

    loop {
        tokio::select! {
            _ = recovery_ticker.tick(), if recovery_enabled => {
                let reset = reset_stale_running_jobs(&conn, stale_running_secs).await?;
                let failed_requeued = if failed_retry_enabled {
                    requeue_stale_failed_no_source_data_jobs(
                        &conn,
                        failed_retry_after_secs,
                        failed_retry_max_attempts,
                        failed_retry_batch_size,
                    )
                    .await?
                } else {
                    0
                };
                let replay_queued = replay_queued_count(&conn).await?;
                let effective_recovery_batch = if queue_backpressure_enabled {
                    dynamic_reenqueue_batch(
                        recovery_batch_size,
                        replay_queued,
                        queue_backpressure_low,
                        queue_backpressure_high,
                        queue_backpressure_min_batch,
                    )
                } else {
                    recovery_batch_size
                };
                let enqueued = reenqueue_queued_jobs(
                    &conn,
                    &producer,
                    &output_topic,
                    &target_group,
                    effective_recovery_batch,
                    queued_stale_secs,
                    reenqueue_cooldown_secs,
                ).await?;
                if reset > 0
                    || failed_requeued > 0
                    || enqueued > 0
                    || (queue_backpressure_enabled && effective_recovery_batch != recovery_batch_size)
                {
                    eprintln!(
                        "backfill-worker periodic recovery replay_queued={} recovery_batch={} reset_running={} failed_requeued={} re_enqueued={}",
                        replay_queued, effective_recovery_batch, reset, failed_requeued, enqueued
                    );
                }
            }
            item = stream.next() => {
                let Some(item) = item else {
                    break;
                };
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
        }
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

    #[test]
    fn dynamic_batch_stops_at_high_watermark() {
        assert_eq!(dynamic_reenqueue_batch(1000, 120000, 90000, 120000, 100), 0);
    }

    #[test]
    fn dynamic_batch_full_below_low_watermark() {
        assert_eq!(dynamic_reenqueue_batch(1000, 50000, 90000, 120000, 100), 1000);
    }

    #[test]
    fn dynamic_batch_scales_between_watermarks() {
        let batch = dynamic_reenqueue_batch(1000, 105000, 90000, 120000, 100);
        assert_eq!(batch, 550);
    }
}
