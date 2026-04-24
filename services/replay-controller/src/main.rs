use chrono::{DateTime, Duration as ChronoDuration, Timelike, Utc};
use futures_util::StreamExt;
use rdkafka::consumer::{CommitMode, Consumer, StreamConsumer};
use rdkafka::message::BorrowedMessage;
use rdkafka::ClientConfig;
use rdkafka::Message;
use serde_json::Value;
use std::collections::{HashMap, HashSet};
use std::env;
use std::fs;
use tokio_postgres::{Client, NoTls};
use uuid::Uuid;

#[derive(Clone, Debug)]
struct ReplayCommand {
    replay_id: Uuid,
    venue: String,
    canonical_symbol: String,
    timeframe: String,
    start_ts: DateTime<Utc>,
    end_ts: DateTime<Utc>,
    dry_run: bool,
}

#[derive(Clone, Debug)]
struct BarRow {
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

fn minute_bucket(ts: DateTime<Utc>) -> DateTime<Utc> {
    ts.with_second(0)
        .and_then(|v| v.with_nanosecond(0))
        .unwrap_or(ts)
}

fn expected_minutes(start: DateTime<Utc>, end: DateTime<Utc>) -> i64 {
    if end < start {
        return 0;
    }
    (end - start).num_minutes() + 1
}

fn message_payload_json(msg: &BorrowedMessage<'_>) -> Option<Value> {
    let payload = msg.payload_view::<str>()?.ok()?;
    serde_json::from_str::<Value>(payload).ok()
}

fn parse_replay_command(payload: &Value) -> Option<ReplayCommand> {
    let replay_id = payload
        .get("replay_id")
        .and_then(|v| v.as_str())
        .and_then(|s| Uuid::parse_str(s).ok())?;

    let source_topic = payload
        .get("source_topic")
        .and_then(|v| v.as_str())
        .unwrap_or("raw.market.oanda");

    let mut venue = payload
        .get("venue")
        .and_then(|v| v.as_str())
        .unwrap_or_default()
        .to_ascii_lowercase();
    if venue.is_empty() {
        venue = source_topic
            .strip_prefix("raw.market.")
            .unwrap_or("oanda")
            .to_ascii_lowercase();
    }

    let canonical_symbol = payload
        .get("canonical_symbol")
        .and_then(|v| v.as_str())
        .unwrap_or_default()
        .to_ascii_uppercase();
    if canonical_symbol.is_empty() {
        return None;
    }

    let timeframe = payload
        .get("timeframe")
        .and_then(|v| v.as_str())
        .unwrap_or("1m")
        .to_string();

    let start_ts = parse_ts(payload.get("start_ts").and_then(|v| v.as_str()))?;
    let end_ts = parse_ts(payload.get("end_ts").and_then(|v| v.as_str()))?;

    Some(ReplayCommand {
        replay_id,
        venue,
        canonical_symbol,
        timeframe,
        start_ts: minute_bucket(start_ts),
        end_ts: minute_bucket(end_ts),
        dry_run: payload.get("dry_run").and_then(|v| v.as_bool()).unwrap_or(false),
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

async fn ensure_tables(conn: &Client) -> Result<(), tokio_postgres::Error> {
    conn.batch_execute(
        "
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

        CREATE UNIQUE INDEX IF NOT EXISTS uq_backfill_jobs_range
          ON backfill_jobs (venue, canonical_symbol, timeframe, range_start, range_end);

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
        ",
    )
    .await
}

fn load_symbol_registry(path: &str) -> HashMap<(String, String), Vec<String>> {
    let Ok(raw) = fs::read_to_string(path) else {
        return HashMap::new();
    };

    let Ok(value) = serde_json::from_str::<Value>(&raw) else {
        return HashMap::new();
    };

    let Some(rows) = value.get("mappings").and_then(|v| v.as_array()) else {
        return HashMap::new();
    };

    let mut out: HashMap<(String, String), Vec<String>> = HashMap::new();
    for row in rows {
        let venue = row
            .get("venue")
            .and_then(|v| v.as_str())
            .unwrap_or_default()
            .trim()
            .to_ascii_lowercase();
        let canonical = row
            .get("canonical_symbol")
            .and_then(|v| v.as_str())
            .unwrap_or_default()
            .trim()
            .to_ascii_uppercase();
        let broker = row
            .get("broker_symbol")
            .and_then(|v| v.as_str())
            .unwrap_or_default()
            .trim()
            .to_ascii_uppercase();

        if venue.is_empty() || canonical.is_empty() || broker.is_empty() {
            continue;
        }
        out.entry((venue, canonical)).or_default().push(broker);
    }

    out
}

fn oanda_legacy_symbol(symbol: &str) -> Option<String> {
    if symbol.len() == 6 && symbol.chars().all(|ch| ch.is_ascii_alphabetic()) {
        return Some(format!("{}_{}", &symbol[0..3], &symbol[3..6]));
    }
    None
}

fn candidate_broker_symbols(
    registry: &HashMap<(String, String), Vec<String>>,
    venue: &str,
    canonical_symbol: &str,
) -> Vec<String> {
    let mut out = Vec::new();
    out.push(canonical_symbol.to_ascii_uppercase());

    if let Some(mapped) = registry.get(&(venue.to_ascii_lowercase(), canonical_symbol.to_ascii_uppercase())) {
        for symbol in mapped {
            out.push(symbol.to_ascii_uppercase());
        }
    }

    if venue.eq_ignore_ascii_case("oanda") {
        if let Some(v) = oanda_legacy_symbol(canonical_symbol) {
            out.push(v);
        }
    }

    let mut seen = HashSet::new();
    out.retain(|v| seen.insert(v.clone()));
    out
}

async fn fetch_aggregated_bars(
    conn: &Client,
    command: &ReplayCommand,
    broker_symbols: &[String],
) -> Result<Vec<BarRow>, tokio_postgres::Error> {
    let end_exclusive = command.end_ts + ChronoDuration::minutes(1);

    let rows = conn
        .query(
            "
            WITH ticks AS (
              SELECT
                date_trunc('minute', event_ts_received) AS bucket_start,
                event_ts_received AS ts,
                COALESCE(mid, (bid + ask) / 2.0, last) AS price
              FROM raw_tick
              WHERE venue = $1
                AND broker_symbol = ANY($2)
                AND event_ts_received >= $3
                AND event_ts_received < $4
                AND COALESCE(mid, (bid + ask) / 2.0, last) IS NOT NULL
            )
            SELECT
              bucket_start,
              (ARRAY_AGG(price ORDER BY ts ASC))[1] AS open,
              MAX(price) AS high,
              MIN(price) AS low,
              (ARRAY_AGG(price ORDER BY ts DESC))[1] AS close,
              COUNT(*)::bigint AS trade_count,
              MAX(ts) AS last_event_ts
            FROM ticks
            GROUP BY bucket_start
            ORDER BY bucket_start ASC
            ",
            &[
                &command.venue,
                &broker_symbols,
                &command.start_ts,
                &end_exclusive,
            ],
        )
        .await?;

    let mut bars = Vec::with_capacity(rows.len());
    for row in rows {
        bars.push(BarRow {
            bucket_start: row.get(0),
            open: row.get(1),
            high: row.get(2),
            low: row.get(3),
            close: row.get(4),
            trade_count: row.get(5),
            last_event_ts: row.get(6),
        });
    }

    Ok(bars)
}

async fn upsert_ohlcv_bars(
    conn: &Client,
    command: &ReplayCommand,
    bars: &[BarRow],
) -> Result<i64, tokio_postgres::Error> {
    let mut written = 0i64;

    for bar in bars {
        let affected = conn
            .execute(
                "
                INSERT INTO ohlcv_bar (
                  venue, canonical_symbol, timeframe, bucket_start,
                  open, high, low, close, volume, trade_count, last_event_ts
                ) VALUES ($1,$2,'1m',$3,$4,$5,$6,$7,$8,$9,$10)
                ON CONFLICT (venue, canonical_symbol, timeframe, bucket_start)
                DO UPDATE SET
                  open = EXCLUDED.open,
                  high = EXCLUDED.high,
                  low = EXCLUDED.low,
                  close = EXCLUDED.close,
                  volume = EXCLUDED.volume,
                  trade_count = EXCLUDED.trade_count,
                  last_event_ts = GREATEST(ohlcv_bar.last_event_ts, EXCLUDED.last_event_ts),
                  updated_at = now()
                ",
                &[
                    &command.venue,
                    &command.canonical_symbol,
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

        written += i64::try_from(affected).unwrap_or(0);
    }

    Ok(written)
}

async fn is_range_complete(
    conn: &Client,
    command: &ReplayCommand,
) -> Result<bool, tokio_postgres::Error> {
    let row = conn
        .query_one(
            "
            SELECT COUNT(DISTINCT bucket_start)::bigint
            FROM ohlcv_bar
            WHERE venue = $1
              AND canonical_symbol = $2
              AND timeframe = '1m'
              AND bucket_start >= $3
              AND bucket_start <= $4
            ",
            &[
                &command.venue,
                &command.canonical_symbol,
                &command.start_ts,
                &command.end_ts,
            ],
        )
        .await?;

    let actual: i64 = row.get(0);
    Ok(actual >= expected_minutes(command.start_ts, command.end_ts))
}

async fn update_backfill_job_status(
    conn: &Client,
    command: &ReplayCommand,
    status: &str,
) -> Result<(), tokio_postgres::Error> {
    conn.execute(
        "
        UPDATE backfill_jobs
        SET status = $1,
            updated_at = now()
        WHERE venue = $2
          AND canonical_symbol = $3
          AND timeframe = '1m'
          AND range_start = $4
          AND range_end = $5
        ",
        &[
            &status,
            &command.venue,
            &command.canonical_symbol,
            &command.start_ts,
            &command.end_ts,
        ],
    )
    .await?;
    Ok(())
}

async fn mark_backfill_jobs_running(
    conn: &Client,
    command: &ReplayCommand,
) -> Result<(), tokio_postgres::Error> {
    conn.execute(
        "
        UPDATE backfill_jobs
        SET status = 'running',
            attempt_count = attempt_count + 1,
            updated_at = now()
        WHERE venue = $1
          AND canonical_symbol = $2
          AND timeframe = '1m'
          AND range_start = $3
          AND range_end = $4
          AND status IN ('queued', 'failed_no_source_data', 'partial')
        ",
        &[
            &command.venue,
            &command.canonical_symbol,
            &command.start_ts,
            &command.end_ts,
        ],
    )
    .await?;
    Ok(())
}

async fn update_replay_audit(
    conn: &Client,
    replay_id: Uuid,
    status: &str,
    moved_messages: i64,
    error: Option<&str>,
) -> Result<(), tokio_postgres::Error> {
    conn.execute(
        "
        UPDATE replay_audit
        SET status = $2,
            moved_messages = $3,
            completed_at = now(),
            error = $4
        WHERE replay_id = $1
        ",
        &[&replay_id, &status, &moved_messages, &error],
    )
    .await?;
    Ok(())
}

async fn resolve_completed_gaps_for_symbol(
    conn: &Client,
    venue: &str,
    symbol: &str,
) -> Result<(), tokio_postgres::Error> {
    let rows = conn
        .query(
            "
            SELECT gap_id, gap_start, gap_end
            FROM gap_log
            WHERE venue = $1
              AND canonical_symbol = $2
              AND timeframe = '1m'
              AND status IN ('open', 'backfill_queued')
            ",
            &[&venue, &symbol],
        )
        .await?;

    for row in rows {
        let gap_id: Uuid = row.get(0);
        let gap_start: DateTime<Utc> = row.get(1);
        let gap_end: DateTime<Utc> = row.get(2);

        let row_count = conn
            .query_one(
                "
                SELECT COUNT(DISTINCT bucket_start)::bigint
                FROM ohlcv_bar
                WHERE venue = $1
                  AND canonical_symbol = $2
                  AND timeframe = '1m'
                  AND bucket_start >= $3
                  AND bucket_start <= $4
                ",
                &[&venue, &symbol, &gap_start, &gap_end],
            )
            .await?;

        let actual: i64 = row_count.get(0);
        if actual >= expected_minutes(gap_start, gap_end) {
            conn.execute(
                "
                UPDATE gap_log
                SET status = 'resolved',
                    resolved_at = now(),
                    updated_at = now()
                WHERE gap_id = $1
                ",
                &[&gap_id],
            )
            .await?;
        }
    }

    Ok(())
}

async fn process_replay_command(
    conn: &Client,
    command: &ReplayCommand,
    registry: &HashMap<(String, String), Vec<String>>,
) -> Result<(), Box<dyn std::error::Error>> {
    if command.timeframe != "1m" {
        update_replay_audit(
            conn,
            command.replay_id,
            "failed",
            0,
            Some("unsupported timeframe"),
        )
        .await?;
        return Ok(());
    }

    if command.end_ts < command.start_ts {
        update_replay_audit(
            conn,
            command.replay_id,
            "failed",
            0,
            Some("invalid range"),
        )
        .await?;
        return Ok(());
    }

    mark_backfill_jobs_running(conn, command).await?;

    if command.dry_run {
        update_backfill_job_status(conn, command, "dry_run").await?;
        update_replay_audit(conn, command.replay_id, "completed", 0, None).await?;
        return Ok(());
    }

    let broker_symbols = candidate_broker_symbols(registry, &command.venue, &command.canonical_symbol);
    let bars = fetch_aggregated_bars(conn, command, &broker_symbols).await?;
    let written = upsert_ohlcv_bars(conn, command, &bars).await?;
    let complete = is_range_complete(conn, command).await?;

    if complete {
        update_backfill_job_status(conn, command, "completed").await?;
        update_replay_audit(conn, command.replay_id, "completed", written, None).await?;
        resolve_completed_gaps_for_symbol(conn, &command.venue, &command.canonical_symbol).await?;
    } else if written > 0 {
        update_backfill_job_status(conn, command, "partial").await?;
        update_replay_audit(
            conn,
            command.replay_id,
            "partial",
            written,
            Some("range remains incomplete after replay"),
        )
        .await?;
    } else {
        update_backfill_job_status(conn, command, "failed_no_source_data").await?;
        update_replay_audit(
            conn,
            command.replay_id,
            "failed",
            0,
            Some("no source ticks found for requested range"),
        )
        .await?;
    }

    Ok(())
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let service_name = "replay_controller";
    let brokers = env_or("KAFKA_BROKERS", "kafka:9092");
    let input_topic = env_or("REPLAY_INPUT_TOPIC", "replay.commands");
    let group_id = env_or("REPLAY_GROUP_ID", "nitra-replay-controller-v1");
    let db_dsn = env_or(
        "DATABASE_URL",
        "postgresql://trading:trading@timescaledb:5432/trading",
    );
    let registry_path = env_or("REPLAY_SYMBOL_REGISTRY_PATH", "/etc/nitra/registry.v1.json");

    let registry = load_symbol_registry(&registry_path);

    let (conn, connection) = tokio_postgres::connect(&db_dsn, NoTls).await?;
    tokio::spawn(async move {
        if let Err(e) = connection.await {
            eprintln!("postgres connection error: {e}");
        }
    });

    ensure_tables(&conn).await?;

    let consumer: StreamConsumer = ClientConfig::new()
        .set("bootstrap.servers", &brokers)
        .set("group.id", &group_id)
        .set("enable.auto.commit", "false")
        .set("auto.offset.reset", "earliest")
        .create()?;
    consumer.subscribe(&[&input_topic])?;

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

        let payload = outer.get("payload").cloned().unwrap_or(Value::Null);
        if let Some(command) = parse_replay_command(&payload) {
            if let Err(err) = process_replay_command(&conn, &command, &registry).await {
                let msg = err.to_string();
                let _ = update_replay_audit(&conn, command.replay_id, "failed", 0, Some(&msg)).await;
                eprintln!("replay-controller command failed: {}", msg);
            }
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
    fn expected_minutes_inclusive() {
        let start = DateTime::parse_from_rfc3339("2026-04-24T00:00:00Z")
            .expect("start")
            .with_timezone(&Utc);
        let end = DateTime::parse_from_rfc3339("2026-04-24T00:02:00Z")
            .expect("end")
            .with_timezone(&Utc);
        assert_eq!(expected_minutes(start, end), 3);
    }

    #[test]
    fn candidate_symbols_include_oanda_legacy() {
        let registry: HashMap<(String, String), Vec<String>> = HashMap::new();
        let symbols = candidate_broker_symbols(&registry, "oanda", "EURUSD");
        assert!(symbols.contains(&"EURUSD".to_string()));
        assert!(symbols.contains(&"EUR_USD".to_string()));
    }
}
