use chrono::{DateTime, Duration as ChronoDuration, Timelike, Utc};
use futures_util::StreamExt;
use rdkafka::consumer::{CommitMode, Consumer, StreamConsumer};
use rdkafka::message::BorrowedMessage;
use rdkafka::producer::{FutureProducer, FutureRecord};
use rdkafka::ClientConfig;
use rdkafka::Message;
use serde_json::{json, Value};
use std::collections::{HashMap, HashSet};
use std::env;
use std::fs;
use std::time::Duration;
use tokio::time::{interval, MissedTickBehavior};
use tokio_postgres::{Client, NoTls};
use uuid::Uuid;

#[derive(Clone, Debug, Eq, PartialEq, Hash)]
struct MarketKey {
    venue: String,
    symbol: String,
}

#[derive(Clone, Debug)]
struct GapRange {
    start: DateTime<Utc>,
    end: DateTime<Utc>,
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

fn load_markets_from_registry(path: &str) -> Vec<MarketKey> {
    let Ok(raw) = fs::read_to_string(path) else {
        return Vec::new();
    };

    let Ok(value) = serde_json::from_str::<Value>(&raw) else {
        return Vec::new();
    };

    let mut out = Vec::new();
    let Some(rows) = value.get("mappings").and_then(|v| v.as_array()) else {
        return out;
    };

    for row in rows {
        let venue = row
            .get("venue")
            .and_then(|v| v.as_str())
            .unwrap_or_default()
            .trim()
            .to_ascii_lowercase();
        let symbol = row
            .get("canonical_symbol")
            .and_then(|v| v.as_str())
            .unwrap_or_default()
            .trim()
            .to_ascii_uppercase();

        if !venue.is_empty() && !symbol.is_empty() {
            out.push(MarketKey { venue, symbol });
        }
    }

    out
}

async fn load_markets_from_db(
    conn: &Client,
    lookback_hours: i64,
) -> Result<Vec<MarketKey>, tokio_postgres::Error> {
    let mut out = Vec::new();

    let bars_recent = conn
        .query(
            "
            SELECT DISTINCT venue, canonical_symbol
            FROM ohlcv_bar
            WHERE timeframe = '1m'
              AND bucket_start >= now() - ($1::text || ' hours')::interval
            ",
            &[&lookback_hours.to_string()],
        )
        .await?;

    for row in bars_recent {
        let venue: String = row.get(0);
        let symbol: String = row.get(1);
        if !venue.is_empty() && !symbol.is_empty() {
            out.push(MarketKey {
                venue: venue.to_ascii_lowercase(),
                symbol: symbol.to_ascii_uppercase(),
            });
        }
    }

    let coverage_recent = conn
        .query(
            "
            SELECT DISTINCT venue, canonical_symbol
            FROM coverage_state
            WHERE timeframe = '1m'
              AND last_seen_at >= now() - ($1::text || ' hours')::interval
            ",
            &[&lookback_hours.to_string()],
        )
        .await?;

    for row in coverage_recent {
        let venue: String = row.get(0);
        let symbol: String = row.get(1);
        if !venue.is_empty() && !symbol.is_empty() {
            out.push(MarketKey {
                venue: venue.to_ascii_lowercase(),
                symbol: symbol.to_ascii_uppercase(),
            });
        }
    }

    Ok(out)
}

fn dedupe_markets(markets: Vec<MarketKey>) -> Vec<MarketKey> {
    let mut seen: HashSet<MarketKey> = HashSet::new();
    let mut out = Vec::new();

    for market in markets {
        if seen.insert(market.clone()) {
            out.push(market);
        }
    }

    out.sort_by(|a, b| {
        let ord = a.venue.cmp(&b.venue);
        if ord != std::cmp::Ordering::Equal {
            return ord;
        }
        a.symbol.cmp(&b.symbol)
    });

    out
}

async fn fetch_buckets_in_window(
    conn: &Client,
    market: &MarketKey,
    start: DateTime<Utc>,
    end: DateTime<Utc>,
) -> Result<Vec<DateTime<Utc>>, tokio_postgres::Error> {
    let rows = conn
        .query(
            "
            SELECT bucket_start
            FROM ohlcv_bar
            WHERE venue = $1
              AND canonical_symbol = $2
              AND timeframe = '1m'
              AND bucket_start >= $3
              AND bucket_start <= $4
            ORDER BY bucket_start ASC
            ",
            &[&market.venue, &market.symbol, &start, &end],
        )
        .await?;

    let mut out = Vec::with_capacity(rows.len());
    for row in rows {
        let ts: DateTime<Utc> = row.get(0);
        out.push(minute_bucket(ts));
    }

    out.dedup();
    Ok(out)
}

fn find_missing_ranges_in_window(
    start: DateTime<Utc>,
    end: DateTime<Utc>,
    buckets: &[DateTime<Utc>],
) -> Vec<GapRange> {
    if end < start {
        return Vec::new();
    }

    let mut ranges = Vec::new();
    let mut cursor = start;

    for bucket in buckets {
        let b = minute_bucket(*bucket);
        if b < cursor {
            continue;
        }
        if b > end {
            break;
        }
        if b > cursor {
            ranges.push(GapRange {
                start: cursor,
                end: b - ChronoDuration::minutes(1),
            });
        }
        cursor = b + ChronoDuration::minutes(1);
        if cursor > end {
            break;
        }
    }

    if cursor <= end {
        ranges.push(GapRange { start: cursor, end });
    }

    ranges
}

async fn upsert_coverage_state(
    conn: &Client,
    venue: &str,
    symbol: &str,
    bucket_start: DateTime<Utc>,
) -> Result<(), tokio_postgres::Error> {
    conn.execute(
        "
        INSERT INTO coverage_state (venue, canonical_symbol, timeframe, last_bucket_start, last_seen_at)
        VALUES ($1, $2, '1m', $3, now())
        ON CONFLICT (venue, canonical_symbol, timeframe)
        DO UPDATE SET
          last_bucket_start = GREATEST(coverage_state.last_bucket_start, EXCLUDED.last_bucket_start),
          last_seen_at = now(),
          updated_at = now();
        ",
        &[&venue, &symbol, &bucket_start],
    )
    .await?;
    Ok(())
}

async fn insert_and_maybe_emit_gap(
    conn: &Client,
    producer: &FutureProducer,
    output_topic: &str,
    venue: &str,
    symbol: &str,
    gap_start: DateTime<Utc>,
    gap_end: DateTime<Utc>,
    source: &str,
    reason: &str,
    last_observed_bucket: Option<DateTime<Utc>>,
    new_observed_bucket: Option<DateTime<Utc>>,
) -> Result<(), Box<dyn std::error::Error>> {
    let gap_id = Uuid::new_v4();
    let detected_at = Utc::now();

    let inserted = conn
        .execute(
            "
            INSERT INTO gap_log (
              gap_id, venue, canonical_symbol, timeframe,
              gap_start, gap_end, detected_at, status,
              source, reason, last_observed_bucket, new_observed_bucket
            )
            VALUES ($1,$2,$3,'1m',$4,$5,$6,'open',$7,$8,$9,$10)
            ON CONFLICT (venue, canonical_symbol, timeframe, gap_start, gap_end)
            DO NOTHING
            ",
            &[
                &gap_id,
                &venue,
                &symbol,
                &gap_start,
                &gap_end,
                &detected_at,
                &source,
                &reason,
                &last_observed_bucket,
                &new_observed_bucket,
            ],
        )
        .await?;

    if inserted == 0 {
        return Ok(());
    }

    let gap_event = json!({
        "gap_id": gap_id.to_string(),
        "venue": venue,
        "canonical_symbol": symbol,
        "timeframe": "1m",
        "gap_start": gap_start.to_rfc3339(),
        "gap_end": gap_end.to_rfc3339(),
        "detected_at": detected_at.to_rfc3339(),
        "source": source,
        "reason": reason,
        "last_observed_bucket": last_observed_bucket.map(|v| v.to_rfc3339()),
        "new_observed_bucket": new_observed_bucket.map(|v| v.to_rfc3339()),
    });

    let wrapped = build_envelope(gap_event).to_string();
    let key = format!("{}:{}", venue, symbol);
    producer
        .send(
            FutureRecord::to(output_topic).key(&key).payload(&wrapped),
            Duration::from_secs(5),
        )
        .await
        .map_err(|(e, _)| e)?;

    Ok(())
}

async fn run_coverage_scan(
    conn: &Client,
    producer: &FutureProducer,
    output_topic: &str,
    registry_path: &str,
    coverage_days: i64,
    db_lookback_hours: i64,
    max_markets: Option<usize>,
    source: &str,
    reason: &str,
) -> Result<usize, Box<dyn std::error::Error>> {
    let mut markets = load_markets_from_registry(registry_path);
    markets.extend(load_markets_from_db(conn, db_lookback_hours).await?);
    let mut markets = dedupe_markets(markets);
    if let Some(max) = max_markets {
        if markets.len() > max {
            markets.truncate(max);
        }
    }

    if markets.is_empty() {
        return Ok(0);
    }

    let scan_end = minute_bucket(Utc::now());
    let scan_start = scan_end - ChronoDuration::days(coverage_days.max(1));

    let mut total_gaps = 0usize;
    for market in markets {
        let buckets = fetch_buckets_in_window(conn, &market, scan_start, scan_end).await?;
        if let Some(last) = buckets.last().copied() {
            upsert_coverage_state(conn, &market.venue, &market.symbol, last).await?;
        }

        let ranges = find_missing_ranges_in_window(scan_start, scan_end, &buckets);
        for range in ranges {
            total_gaps += 1;
            insert_and_maybe_emit_gap(
                conn,
                producer,
                output_topic,
                &market.venue,
                &market.symbol,
                range.start,
                range.end,
                source,
                reason,
                None,
                None,
            )
            .await?;
        }
    }

    Ok(total_gaps)
}

async fn load_last_bucket_from_coverage_state(
    conn: &Client,
    venue: &str,
    symbol: &str,
) -> Result<Option<DateTime<Utc>>, tokio_postgres::Error> {
    let row = conn
        .query_opt(
            "
            SELECT last_bucket_start
            FROM coverage_state
            WHERE venue = $1
              AND canonical_symbol = $2
              AND timeframe = '1m'
            ",
            &[&venue, &symbol],
        )
        .await?;
    Ok(row.map(|r| {
        let ts: DateTime<Utc> = r.get(0);
        minute_bucket(ts)
    }))
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

    let startup_scan_enabled = env_bool_or("GAP_STARTUP_SCAN_ENABLED", true);
    // Hard floor: platform rule requires at least rolling 90-day 1m coverage.
    let startup_coverage_days = env_i64_or("GAP_STARTUP_COVERAGE_DAYS", 90).max(90);
    let startup_db_lookback_hours = env_i64_or("GAP_ACTIVE_MARKET_DB_LOOKBACK_HOURS", 24);
    let registry_path = env_or("GAP_SYMBOL_REGISTRY_PATH", "/etc/nitra/registry.v1.json");
    let periodic_scan_enabled = env_bool_or("GAP_PERIODIC_SCAN_ENABLED", true);
    let periodic_scan_interval_secs = env_i64_or("GAP_PERIODIC_SCAN_INTERVAL_SECS", 300).max(30);
    let periodic_scan_markets_per_cycle = env_i64_or("GAP_PERIODIC_SCAN_MARKETS_PER_CYCLE", 64).max(1) as usize;

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

    if startup_scan_enabled {
        let emitted = run_coverage_scan(
            &conn,
            &producer,
            &output_topic,
            &registry_path,
            startup_coverage_days,
            startup_db_lookback_hours,
            None,
            "startup_coverage_scan",
            "startup_90d_missing",
        )
        .await?;
        eprintln!(
            "gap-detection startup coverage scan complete: emitted_or_recorded_gaps={} window_days={}",
            emitted, startup_coverage_days
        );
    }

    let mut last_bucket: HashMap<(String, String), DateTime<Utc>> = HashMap::new();
    let mut stream = consumer.stream();
    let mut periodic_scan_tick = interval(Duration::from_secs(periodic_scan_interval_secs as u64));
    periodic_scan_tick.set_missed_tick_behavior(MissedTickBehavior::Skip);
    if periodic_scan_enabled {
        periodic_scan_tick.tick().await;
    }

    loop {
        tokio::select! {
            _ = periodic_scan_tick.tick(), if periodic_scan_enabled => {
                match run_coverage_scan(
                    &conn,
                    &producer,
                    &output_topic,
                    &registry_path,
                    startup_coverage_days,
                    startup_db_lookback_hours,
                    Some(periodic_scan_markets_per_cycle),
                    "periodic_coverage_scan",
                    "periodic_90d_missing",
                ).await {
                    Ok(emitted) => {
                        if emitted > 0 {
                            eprintln!(
                                "gap-detection periodic coverage scan emitted_or_recorded_gaps={} window_days={} markets_limit={}",
                                emitted, startup_coverage_days, periodic_scan_markets_per_cycle
                            );
                        }
                    }
                    Err(err) => {
                        eprintln!("gap-detection periodic coverage scan error: {err}");
                    }
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

                let bucket = minute_bucket(parse_ts(bucket_raw));
                let key = (venue.to_ascii_lowercase(), symbol.to_ascii_uppercase());
                let mut gap_source = "stream";
                let mut gap_reason = "missing_minute_bars";
                if !last_bucket.contains_key(&key) {
                    if let Some(previous) =
                        load_last_bucket_from_coverage_state(&conn, &key.0, &key.1).await?
                    {
                        last_bucket.insert(key.clone(), previous);
                        gap_source = "stream_recovery";
                        gap_reason = "missing_minute_bars_after_downtime";
                    }
                }

                if let Some(previous) = last_bucket.get(&key).copied() {
                    if bucket > previous + ChronoDuration::minutes(1) {
                        let gap_start = previous + ChronoDuration::minutes(1);
                        let gap_end = bucket - ChronoDuration::minutes(1);
                        insert_and_maybe_emit_gap(
                            &conn,
                            &producer,
                            &output_topic,
                            venue,
                            symbol,
                            gap_start,
                            gap_end,
                            gap_source,
                            gap_reason,
                            Some(previous),
                            Some(bucket),
                        )
                        .await?;
                    }
                }
                last_bucket.insert(key, bucket);
                upsert_coverage_state(&conn, venue, symbol, bucket).await?;

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
    fn missing_ranges_detects_leading_internal_and_trailing() {
        let start = DateTime::parse_from_rfc3339("2026-01-01T00:00:00Z")
            .expect("start")
            .with_timezone(&Utc);
        let end = DateTime::parse_from_rfc3339("2026-01-01T00:06:00Z")
            .expect("end")
            .with_timezone(&Utc);
        let buckets = vec![
            DateTime::parse_from_rfc3339("2026-01-01T00:01:00Z")
                .expect("bucket")
                .with_timezone(&Utc),
            DateTime::parse_from_rfc3339("2026-01-01T00:02:00Z")
                .expect("bucket")
                .with_timezone(&Utc),
            DateTime::parse_from_rfc3339("2026-01-01T00:05:00Z")
                .expect("bucket")
                .with_timezone(&Utc),
        ];

        let gaps = find_missing_ranges_in_window(start, end, &buckets);
        assert_eq!(gaps.len(), 3);
        assert_eq!(gaps[0].start.to_rfc3339(), "2026-01-01T00:00:00+00:00");
        assert_eq!(gaps[0].end.to_rfc3339(), "2026-01-01T00:00:00+00:00");
        assert_eq!(gaps[1].start.to_rfc3339(), "2026-01-01T00:03:00+00:00");
        assert_eq!(gaps[1].end.to_rfc3339(), "2026-01-01T00:04:00+00:00");
        assert_eq!(gaps[2].start.to_rfc3339(), "2026-01-01T00:06:00+00:00");
        assert_eq!(gaps[2].end.to_rfc3339(), "2026-01-01T00:06:00+00:00");
    }

    #[test]
    fn missing_ranges_full_window_when_no_bars() {
        let start = DateTime::parse_from_rfc3339("2026-01-01T00:00:00Z")
            .expect("start")
            .with_timezone(&Utc);
        let end = DateTime::parse_from_rfc3339("2026-01-01T00:02:00Z")
            .expect("end")
            .with_timezone(&Utc);

        let gaps = find_missing_ranges_in_window(start, end, &[]);
        assert_eq!(gaps.len(), 1);
        assert_eq!(gaps[0].start, start);
        assert_eq!(gaps[0].end, end);
    }
}
