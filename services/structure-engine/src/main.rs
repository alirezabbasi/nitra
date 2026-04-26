use chrono::{DateTime, Utc};
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

#[derive(Clone, Debug)]
struct BarInput {
    venue: String,
    canonical_symbol: String,
    timeframe: String,
    bucket_start: DateTime<Utc>,
    open: f64,
    high: f64,
    low: f64,
    close: f64,
    last_event_ts: DateTime<Utc>,
}

#[derive(Clone, Debug)]
struct StructureState {
    trend: String,
    phase: String,
    objective: String,
    swing_high: f64,
    swing_low: f64,
    last_bucket_start: DateTime<Utc>,
    last_close: f64,
    extension_count: i32,
    pullback_count: i32,
    inside_bars: i32,
    outside_bars: i32,
}

#[derive(Clone, Debug)]
struct TransitionFlags {
    emit_pullback: bool,
    emit_minor: bool,
    emit_major: bool,
    reason: String,
}

fn env_or(name: &str, default: &str) -> String {
    env::var(name).unwrap_or_else(|_| default.to_string())
}

fn parse_ts(value: Option<&str>) -> Option<DateTime<Utc>> {
    let raw = value?;
    DateTime::parse_from_rfc3339(raw)
        .map(|v| v.with_timezone(&Utc))
        .ok()
        .or_else(|| {
            DateTime::parse_from_rfc3339(&raw.replace('Z', "+00:00"))
                .map(|v| v.with_timezone(&Utc))
                .ok()
        })
}

fn parse_bar(payload: &Value) -> Option<BarInput> {
    let venue = payload.get("venue")?.as_str()?.trim().to_ascii_lowercase();
    let canonical_symbol = payload
        .get("canonical_symbol")?
        .as_str()?
        .trim()
        .to_ascii_uppercase();
    let timeframe = payload
        .get("timeframe")
        .and_then(|v| v.as_str())
        .unwrap_or("1m")
        .to_string();
    let bucket_start = parse_ts(payload.get("bucket_start").and_then(|v| v.as_str()))?;
    let last_event_ts = parse_ts(payload.get("last_event_ts").and_then(|v| v.as_str()))
        .unwrap_or(bucket_start);
    let open = payload.get("open")?.as_f64()?;
    let high = payload.get("high")?.as_f64()?;
    let low = payload.get("low")?.as_f64()?;
    let close = payload.get("close")?.as_f64()?;

    if venue.is_empty() || canonical_symbol.is_empty() {
        return None;
    }

    Some(BarInput {
        venue,
        canonical_symbol,
        timeframe,
        bucket_start,
        open,
        high,
        low,
        close,
        last_event_ts,
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

fn objective_for_trend(trend: &str) -> &'static str {
    match trend {
        "bullish" => "buy_side",
        "bearish" => "sell_side",
        _ => "none",
    }
}

fn apply_bar_transition(prev: Option<&StructureState>, bar: &BarInput) -> (StructureState, TransitionFlags) {
    let Some(previous) = prev else {
        return (
            StructureState {
                trend: "neutral".to_string(),
                phase: "init".to_string(),
                objective: "none".to_string(),
                swing_high: bar.high,
                swing_low: bar.low,
                last_bucket_start: bar.bucket_start,
                last_close: bar.close,
                extension_count: 0,
                pullback_count: 0,
                inside_bars: 0,
                outside_bars: 0,
            },
            TransitionFlags {
                emit_pullback: false,
                emit_minor: false,
                emit_major: false,
                reason: "initialization".to_string(),
            },
        );
    };

    let inside = bar.high <= previous.swing_high && bar.low >= previous.swing_low;
    let outside = bar.high >= previous.swing_high && bar.low <= previous.swing_low;

    let broke_up = bar.close > previous.swing_high;
    let broke_down = bar.close < previous.swing_low;

    let mut trend = previous.trend.clone();
    if broke_up && !broke_down {
        trend = "bullish".to_string();
    } else if broke_down && !broke_up {
        trend = "bearish".to_string();
    } else if broke_up && broke_down {
        let up_delta = (bar.close - previous.swing_high).abs();
        let down_delta = (previous.swing_low - bar.close).abs();
        trend = if up_delta >= down_delta {
            "bullish".to_string()
        } else {
            "bearish".to_string()
        };
    }

    let trend_changed = trend != previous.trend && trend != "neutral";

    let (phase, extension_count, pullback_count, emit_pullback, emit_minor, reason) =
        if trend_changed {
            (
                "extension".to_string(),
                1,
                0,
                false,
                true,
                "trend_shift".to_string(),
            )
        } else {
            let is_pullback = (trend == "bullish" && bar.close < previous.last_close)
                || (trend == "bearish" && bar.close > previous.last_close);

            if is_pullback {
                (
                    "pullback".to_string(),
                    0,
                    previous.pullback_count + 1,
                    true,
                    false,
                    "pullback".to_string(),
                )
            } else {
                (
                    "extension".to_string(),
                    previous.extension_count + 1,
                    previous.pullback_count,
                    false,
                    false,
                    "extension".to_string(),
                )
            }
        };

    let emit_major = trend != "neutral" && phase == "extension" && extension_count >= 3;
    let objective = objective_for_trend(&trend).to_string();

    let (swing_high, swing_low) = if trend_changed {
        (bar.high, bar.low)
    } else {
        (previous.swing_high.max(bar.high), previous.swing_low.min(bar.low))
    };

    (
        StructureState {
            trend,
            phase,
            objective,
            swing_high,
            swing_low,
            last_bucket_start: bar.bucket_start,
            last_close: bar.close,
            extension_count,
            pullback_count,
            inside_bars: previous.inside_bars + if inside { 1 } else { 0 },
            outside_bars: previous.outside_bars + if outside { 1 } else { 0 },
        },
        TransitionFlags {
            emit_pullback,
            emit_minor,
            emit_major,
            reason,
        },
    )
}

async fn ensure_structure_tables(conn: &Client) -> Result<(), tokio_postgres::Error> {
    conn.batch_execute(
        "
        CREATE TABLE IF NOT EXISTS structure_state (
          venue TEXT NOT NULL,
          canonical_symbol TEXT NOT NULL,
          timeframe TEXT NOT NULL DEFAULT '1m',
          trend TEXT NOT NULL DEFAULT 'neutral',
          phase TEXT NOT NULL DEFAULT 'init',
          objective TEXT NOT NULL DEFAULT 'none',
          swing_high DOUBLE PRECISION NOT NULL,
          swing_low DOUBLE PRECISION NOT NULL,
          last_bucket_start TIMESTAMPTZ NOT NULL,
          last_close DOUBLE PRECISION NOT NULL,
          extension_count INT NOT NULL DEFAULT 0,
          pullback_count INT NOT NULL DEFAULT 0,
          inside_bars INT NOT NULL DEFAULT 0,
          outside_bars INT NOT NULL DEFAULT 0,
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          PRIMARY KEY (venue, canonical_symbol, timeframe)
        );

        CREATE INDEX IF NOT EXISTS idx_structure_state_updated
          ON structure_state (updated_at DESC);
        "
    ).await
}

async fn load_state(
    conn: &Client,
    venue: &str,
    symbol: &str,
    timeframe: &str,
) -> Result<Option<StructureState>, tokio_postgres::Error> {
    let row = conn
        .query_opt(
            "
            SELECT trend, phase, objective, swing_high, swing_low,
                   last_bucket_start, last_close, extension_count,
                   pullback_count, inside_bars, outside_bars
            FROM structure_state
            WHERE venue = $1 AND canonical_symbol = $2 AND timeframe = $3
            ",
            &[&venue, &symbol, &timeframe],
        )
        .await?;

    let Some(row) = row else {
        return Ok(None);
    };

    Ok(Some(StructureState {
        trend: row.get::<_, String>(0),
        phase: row.get::<_, String>(1),
        objective: row.get::<_, String>(2),
        swing_high: row.get::<_, f64>(3),
        swing_low: row.get::<_, f64>(4),
        last_bucket_start: row.get::<_, DateTime<Utc>>(5),
        last_close: row.get::<_, f64>(6),
        extension_count: row.get::<_, i32>(7),
        pullback_count: row.get::<_, i32>(8),
        inside_bars: row.get::<_, i32>(9),
        outside_bars: row.get::<_, i32>(10),
    }))
}

async fn persist_state(
    conn: &Client,
    venue: &str,
    symbol: &str,
    timeframe: &str,
    state: &StructureState,
) -> Result<(), tokio_postgres::Error> {
    conn.execute(
        "
        INSERT INTO structure_state (
          venue, canonical_symbol, timeframe, trend, phase, objective,
          swing_high, swing_low, last_bucket_start, last_close,
          extension_count, pullback_count, inside_bars, outside_bars
        ) VALUES (
          $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14
        )
        ON CONFLICT (venue, canonical_symbol, timeframe)
        DO UPDATE SET
          trend = EXCLUDED.trend,
          phase = EXCLUDED.phase,
          objective = EXCLUDED.objective,
          swing_high = EXCLUDED.swing_high,
          swing_low = EXCLUDED.swing_low,
          last_bucket_start = EXCLUDED.last_bucket_start,
          last_close = EXCLUDED.last_close,
          extension_count = EXCLUDED.extension_count,
          pullback_count = EXCLUDED.pullback_count,
          inside_bars = EXCLUDED.inside_bars,
          outside_bars = EXCLUDED.outside_bars,
          updated_at = now()
        ",
        &[
            &venue,
            &symbol,
            &timeframe,
            &state.trend,
            &state.phase,
            &state.objective,
            &state.swing_high,
            &state.swing_low,
            &state.last_bucket_start,
            &state.last_close,
            &state.extension_count,
            &state.pullback_count,
            &state.inside_bars,
            &state.outside_bars,
        ],
    )
    .await?;
    Ok(())
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

async fn publish_event(
    producer: &FutureProducer,
    topic: &str,
    key: &str,
    payload: Value,
) -> Result<(), Box<dyn std::error::Error>> {
    let wrapped = build_envelope(payload).to_string();
    producer
        .send(
            FutureRecord::to(topic).key(key).payload(&wrapped),
            Duration::from_secs(5),
        )
        .await
        .map_err(|(e, _)| e)?;
    Ok(())
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let service_name = "structure_engine";

    let brokers = env_or("KAFKA_BROKERS", "kafka:9092");
    let input_topic = env_or("STRUCTURE_INPUT_TOPIC", "bar.1m");
    let snapshot_topic = env_or("STRUCTURE_SNAPSHOT_TOPIC", "structure.snapshot.v1");
    let pullback_topic = env_or("STRUCTURE_PULLBACK_TOPIC", "structure.pullback.v1");
    let minor_topic = env_or("STRUCTURE_MINOR_TOPIC", "structure.minor_confirmed.v1");
    let major_topic = env_or("STRUCTURE_MAJOR_TOPIC", "structure.major_confirmed.v1");
    let group_id = env_or("STRUCTURE_GROUP_ID", "nitra-structure-engine-v1");
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

    ensure_structure_tables(&conn).await?;

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

    let mut stream = consumer.stream();
    let mut state_cache: HashMap<(String, String, String), StructureState> = HashMap::new();

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
        let Some(bar) = parse_bar(&payload) else {
            consumer.commit_message(&msg, CommitMode::Sync)?;
            continue;
        };

        let cache_key = (
            bar.venue.clone(),
            bar.canonical_symbol.clone(),
            bar.timeframe.clone(),
        );

        let previous = if let Some(state) = state_cache.get(&cache_key) {
            Some(state.clone())
        } else {
            let loaded = load_state(&conn, &bar.venue, &bar.canonical_symbol, &bar.timeframe).await?;
            if let Some(found) = loaded.clone() {
                state_cache.insert(cache_key.clone(), found);
            }
            loaded
        };

        let (new_state, flags) = apply_bar_transition(previous.as_ref(), &bar);

        persist_state(
            &conn,
            &bar.venue,
            &bar.canonical_symbol,
            &bar.timeframe,
            &new_state,
        )
        .await?;

        let event_key = format!("{}:{}:{}", bar.venue, bar.canonical_symbol, bar.timeframe);

        let snapshot_payload = json!({
            "venue": bar.venue,
            "canonical_symbol": bar.canonical_symbol,
            "timeframe": bar.timeframe,
            "bucket_start": bar.bucket_start.to_rfc3339(),
            "last_event_ts": bar.last_event_ts.to_rfc3339(),
            "input_bar": {
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
            },
            "state": {
                "trend": new_state.trend,
                "phase": new_state.phase,
                "objective": new_state.objective,
                "swing_high": new_state.swing_high,
                "swing_low": new_state.swing_low,
                "last_close": new_state.last_close,
                "extension_count": new_state.extension_count,
                "pullback_count": new_state.pullback_count,
                "inside_bars": new_state.inside_bars,
                "outside_bars": new_state.outside_bars,
            },
            "transition_reason": flags.reason,
        });

        publish_event(&producer, &snapshot_topic, &event_key, snapshot_payload).await?;

        if flags.emit_pullback {
            let pullback_payload = json!({
                "venue": bar.venue,
                "canonical_symbol": bar.canonical_symbol,
                "timeframe": bar.timeframe,
                "bucket_start": bar.bucket_start.to_rfc3339(),
                "trend": new_state.trend,
                "objective": new_state.objective,
                "pullback_count": new_state.pullback_count,
                "last_close": new_state.last_close,
            });
            publish_event(&producer, &pullback_topic, &event_key, pullback_payload).await?;
        }

        if flags.emit_minor {
            let minor_payload = json!({
                "venue": bar.venue,
                "canonical_symbol": bar.canonical_symbol,
                "timeframe": bar.timeframe,
                "bucket_start": bar.bucket_start.to_rfc3339(),
                "trend": new_state.trend,
                "phase": new_state.phase,
                "objective": new_state.objective,
                "reason": "trend_shift",
            });
            publish_event(&producer, &minor_topic, &event_key, minor_payload).await?;
        }

        if flags.emit_major {
            let major_payload = json!({
                "venue": bar.venue,
                "canonical_symbol": bar.canonical_symbol,
                "timeframe": bar.timeframe,
                "bucket_start": bar.bucket_start.to_rfc3339(),
                "trend": new_state.trend,
                "objective": new_state.objective,
                "extension_count": new_state.extension_count,
                "swing_high": new_state.swing_high,
                "swing_low": new_state.swing_low,
            });
            publish_event(&producer, &major_topic, &event_key, major_payload).await?;
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

        state_cache.insert(cache_key, new_state);
        consumer.commit_message(&msg, CommitMode::Sync)?;
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn mk_bar(close: f64, high: f64, low: f64, minute: i64) -> BarInput {
        let ts = DateTime::from_timestamp(minute * 60, 0)
            .unwrap_or_else(Utc::now)
            .with_timezone(&Utc);
        BarInput {
            venue: "coinbase".to_string(),
            canonical_symbol: "BTCUSD".to_string(),
            timeframe: "1m".to_string(),
            bucket_start: ts,
            open: close,
            high,
            low,
            close,
            last_event_ts: ts,
        }
    }

    #[test]
    fn initializes_neutral_state() {
        let bar = mk_bar(100.0, 101.0, 99.0, 1);
        let (state, flags) = apply_bar_transition(None, &bar);
        assert_eq!(state.trend, "neutral");
        assert_eq!(state.phase, "init");
        assert!(!flags.emit_minor);
        assert!(!flags.emit_pullback);
    }

    #[test]
    fn emits_minor_on_trend_shift() {
        let first = mk_bar(100.0, 101.0, 99.0, 1);
        let (init_state, _) = apply_bar_transition(None, &first);

        let second = mk_bar(105.0, 106.0, 100.0, 2);
        let (state, flags) = apply_bar_transition(Some(&init_state), &second);

        assert_eq!(state.trend, "bullish");
        assert!(flags.emit_minor);
    }

    #[test]
    fn emits_pullback_when_bullish_and_close_drops() {
        let first = mk_bar(100.0, 101.0, 99.0, 1);
        let (init_state, _) = apply_bar_transition(None, &first);

        let second = mk_bar(105.0, 106.0, 100.0, 2);
        let (bull_state, _) = apply_bar_transition(Some(&init_state), &second);

        let third = mk_bar(103.0, 104.0, 102.0, 3);
        let (state, flags) = apply_bar_transition(Some(&bull_state), &third);

        assert_eq!(state.phase, "pullback");
        assert!(flags.emit_pullback);
    }

    #[test]
    fn emits_major_after_three_extensions() {
        let b1 = mk_bar(100.0, 101.0, 99.0, 1);
        let (s1, _) = apply_bar_transition(None, &b1);

        let b2 = mk_bar(105.0, 106.0, 100.0, 2);
        let (s2, _) = apply_bar_transition(Some(&s1), &b2);

        let b3 = mk_bar(107.0, 108.0, 104.0, 3);
        let (s3, _) = apply_bar_transition(Some(&s2), &b3);

        let b4 = mk_bar(109.0, 110.0, 106.0, 4);
        let (_s4, flags4) = apply_bar_transition(Some(&s3), &b4);

        assert!(flags4.emit_major);
    }
}
