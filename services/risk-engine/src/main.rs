use chrono::{DateTime, Utc};
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
struct RiskInput {
    venue: String,
    canonical_symbol: String,
    timeframe: String,
    side: String,
    confidence: f64,
    requested_notional: f64,
    event_ts: DateTime<Utc>,
    source_kind: String,
}

#[derive(Clone, Debug)]
struct RiskState {
    current_exposure_notional: f64,
    equity: f64,
    drawdown_pct: f64,
    kill_switch_enabled: bool,
}

#[derive(Clone, Debug)]
struct RiskPolicy {
    min_confidence: f64,
    max_notional: f64,
    max_drawdown_pct: f64,
}

#[derive(Clone, Debug)]
struct RiskDecision {
    approved: bool,
    reason: String,
    violations: Vec<String>,
    side: String,
    accepted_notional: f64,
}

fn env_or(name: &str, default: &str) -> String {
    env::var(name).unwrap_or_else(|_| default.to_string())
}

fn env_f64_or(name: &str, default: f64) -> f64 {
    env::var(name)
        .ok()
        .and_then(|v| v.parse::<f64>().ok())
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

fn parse_side(raw: &str) -> String {
    let normalized = raw.trim().to_ascii_lowercase();
    match normalized.as_str() {
        "buy" | "sell" => normalized,
        "buy_side" => "buy".to_string(),
        "sell_side" => "sell".to_string(),
        _ => "hold".to_string(),
    }
}

fn parse_risk_input(payload: &Value, default_notional: f64) -> Option<RiskInput> {
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

    let signal = payload.get("signal").cloned().unwrap_or(Value::Null);
    let source_kind = if signal.is_object() {
        "signal_scored".to_string()
    } else {
        "structure_snapshot".to_string()
    };

    let side_raw = signal
        .get("side")
        .and_then(|v| v.as_str())
        .or_else(|| payload.get("side").and_then(|v| v.as_str()))
        .or_else(|| {
            payload
                .get("state")
                .and_then(|v| v.get("objective"))
                .and_then(|v| v.as_str())
        })
        .unwrap_or("hold");

    let side = parse_side(side_raw);

    let confidence = signal
        .get("confidence")
        .and_then(|v| v.as_f64())
        .or_else(|| payload.get("confidence").and_then(|v| v.as_f64()))
        .unwrap_or(0.5)
        .clamp(0.0, 1.0);

    let requested_notional = signal
        .get("notional_requested")
        .and_then(|v| v.as_f64())
        .or_else(|| payload.get("notional_requested").and_then(|v| v.as_f64()))
        .or_else(|| payload.get("notional").and_then(|v| v.as_f64()))
        .unwrap_or(default_notional)
        .abs();

    let event_ts = parse_ts(payload.get("bucket_start").and_then(|v| v.as_str()))
        .or_else(|| parse_ts(payload.get("event_ts").and_then(|v| v.as_str())))
        .or_else(|| parse_ts(payload.get("last_event_ts").and_then(|v| v.as_str())))
        .unwrap_or_else(Utc::now);

    if venue.is_empty() || canonical_symbol.is_empty() {
        return None;
    }

    Some(RiskInput {
        venue,
        canonical_symbol,
        timeframe,
        side,
        confidence,
        requested_notional,
        event_ts,
        source_kind,
    })
}

fn evaluate_policy(input: &RiskInput, state: &RiskState, policy: &RiskPolicy) -> RiskDecision {
    let mut violations = Vec::new();

    if state.kill_switch_enabled {
        violations.push("kill_switch_enabled".to_string());
    }
    if input.requested_notional > policy.max_notional {
        violations.push("max_notional_exceeded".to_string());
    }
    if state.drawdown_pct > policy.max_drawdown_pct {
        violations.push("max_drawdown_exceeded".to_string());
    }
    if input.side != "hold" && input.confidence < policy.min_confidence {
        violations.push("confidence_below_threshold".to_string());
    }

    if input.side == "hold" {
        return RiskDecision {
            approved: false,
            reason: "no_trade_side".to_string(),
            violations,
            side: input.side.clone(),
            accepted_notional: 0.0,
        };
    }

    if !violations.is_empty() {
        return RiskDecision {
            approved: false,
            reason: "policy_violation".to_string(),
            violations,
            side: input.side.clone(),
            accepted_notional: 0.0,
        };
    }

    RiskDecision {
        approved: true,
        reason: "approved".to_string(),
        violations,
        side: input.side.clone(),
        accepted_notional: input.requested_notional,
    }
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

async fn ensure_risk_tables(conn: &Client) -> Result<(), tokio_postgres::Error> {
    conn.batch_execute(
        "
        CREATE TABLE IF NOT EXISTS risk_state (
          venue TEXT NOT NULL,
          canonical_symbol TEXT NOT NULL,
          timeframe TEXT NOT NULL DEFAULT '1m',
          current_exposure_notional DOUBLE PRECISION NOT NULL DEFAULT 0,
          equity DOUBLE PRECISION NOT NULL DEFAULT 100000,
          drawdown_pct DOUBLE PRECISION NOT NULL DEFAULT 0,
          kill_switch_enabled BOOLEAN NOT NULL DEFAULT FALSE,
          last_decision_at TIMESTAMPTZ,
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          PRIMARY KEY (venue, canonical_symbol, timeframe)
        );

        CREATE TABLE IF NOT EXISTS risk_decision_log (
          decision_id UUID PRIMARY KEY,
          venue TEXT NOT NULL,
          canonical_symbol TEXT NOT NULL,
          timeframe TEXT NOT NULL,
          input_topic TEXT NOT NULL,
          side TEXT NOT NULL,
          requested_notional DOUBLE PRECISION NOT NULL,
          confidence DOUBLE PRECISION NOT NULL,
          approved BOOLEAN NOT NULL,
          reason TEXT NOT NULL,
          violations JSONB NOT NULL DEFAULT '[]'::jsonb,
          event_ts TIMESTAMPTZ NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_risk_decision_log_symbol_ts
          ON risk_decision_log (venue, canonical_symbol, created_at DESC);
        ",
    )
    .await
}

async fn load_risk_state(
    conn: &Client,
    venue: &str,
    symbol: &str,
    timeframe: &str,
) -> Result<RiskState, tokio_postgres::Error> {
    let row = conn
        .query_opt(
            "
            SELECT current_exposure_notional, equity, drawdown_pct, kill_switch_enabled
            FROM risk_state
            WHERE venue = $1 AND canonical_symbol = $2 AND timeframe = $3
            ",
            &[&venue, &symbol, &timeframe],
        )
        .await?;

    if let Some(row) = row {
        return Ok(RiskState {
            current_exposure_notional: row.get::<_, f64>(0),
            equity: row.get::<_, f64>(1),
            drawdown_pct: row.get::<_, f64>(2),
            kill_switch_enabled: row.get::<_, bool>(3),
        });
    }

    Ok(RiskState {
        current_exposure_notional: 0.0,
        equity: 100000.0,
        drawdown_pct: 0.0,
        kill_switch_enabled: false,
    })
}

fn next_exposure(state: &RiskState, decision: &RiskDecision) -> f64 {
    if !decision.approved {
        return state.current_exposure_notional;
    }

    if decision.side == "buy" {
        state.current_exposure_notional + decision.accepted_notional
    } else if decision.side == "sell" {
        (state.current_exposure_notional - decision.accepted_notional).max(0.0)
    } else {
        state.current_exposure_notional
    }
}

async fn persist_risk_state(
    conn: &Client,
    input: &RiskInput,
    state: &RiskState,
    decision: &RiskDecision,
) -> Result<(), tokio_postgres::Error> {
    let exposure = next_exposure(state, decision);
    let now = Utc::now();

    conn.execute(
        "
        INSERT INTO risk_state (
          venue, canonical_symbol, timeframe, current_exposure_notional,
          equity, drawdown_pct, kill_switch_enabled, last_decision_at
        ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
        ON CONFLICT (venue, canonical_symbol, timeframe)
        DO UPDATE SET
          current_exposure_notional = EXCLUDED.current_exposure_notional,
          equity = EXCLUDED.equity,
          drawdown_pct = EXCLUDED.drawdown_pct,
          kill_switch_enabled = EXCLUDED.kill_switch_enabled,
          last_decision_at = EXCLUDED.last_decision_at,
          updated_at = now()
        ",
        &[
            &input.venue,
            &input.canonical_symbol,
            &input.timeframe,
            &exposure,
            &state.equity,
            &state.drawdown_pct,
            &state.kill_switch_enabled,
            &now,
        ],
    )
    .await?;

    Ok(())
}

async fn insert_decision_log(
    conn: &Client,
    input_topic: &str,
    input: &RiskInput,
    decision: &RiskDecision,
) -> Result<(), tokio_postgres::Error> {
    conn.execute(
        "
        INSERT INTO risk_decision_log (
          decision_id, venue, canonical_symbol, timeframe, input_topic,
          side, requested_notional, confidence, approved, reason,
          violations, event_ts
        ) VALUES (
          $1::uuid,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11::jsonb,$12
        )
        ",
        &[
            &Uuid::new_v4(),
            &input.venue,
            &input.canonical_symbol,
            &input.timeframe,
            &input_topic,
            &decision.side,
            &input.requested_notional,
            &input.confidence,
            &decision.approved,
            &decision.reason,
            &json!(decision.violations),
            &input.event_ts,
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
    let service_name = "risk_engine";

    let brokers = env_or("KAFKA_BROKERS", "kafka:9092");
    let input_topic = env_or("RISK_INPUT_TOPIC", "decision.signal_scored.v1");
    let risk_checked_topic = env_or("RISK_CHECKED_TOPIC", "decision.risk_checked.v1");
    let violation_topic = env_or("RISK_VIOLATION_TOPIC", "ops.policy_violation.v1");
    let group_id = env_or("RISK_GROUP_ID", "nitra-risk-engine-v1");
    let db_dsn = env_or(
        "DATABASE_URL",
        "postgresql://trading:trading@timescaledb:5432/trading",
    );

    let policy = RiskPolicy {
        min_confidence: env_f64_or("RISK_MIN_CONFIDENCE", 0.55).clamp(0.0, 1.0),
        max_notional: env_f64_or("RISK_MAX_NOTIONAL", 100000.0).max(1.0),
        max_drawdown_pct: env_f64_or("RISK_MAX_DRAWDOWN_PCT", 5.0).max(0.0),
    };
    let default_notional = env_f64_or("RISK_DEFAULT_NOTIONAL", 1000.0).max(1.0);

    let (conn, connection) = tokio_postgres::connect(&db_dsn, NoTls).await?;
    tokio::spawn(async move {
        if let Err(e) = connection.await {
            eprintln!("postgres connection error: {e}");
        }
    });

    ensure_risk_tables(&conn).await?;

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
        let Some(input) = parse_risk_input(&payload, default_notional) else {
            consumer.commit_message(&msg, CommitMode::Sync)?;
            continue;
        };

        let current_state = load_risk_state(
            &conn,
            &input.venue,
            &input.canonical_symbol,
            &input.timeframe,
        )
        .await?;
        let decision = evaluate_policy(&input, &current_state, &policy);

        persist_risk_state(&conn, &input, &current_state, &decision).await?;
        insert_decision_log(&conn, &source_topic, &input, &decision).await?;

        let event_key = format!(
            "{}:{}:{}",
            input.venue, input.canonical_symbol, input.timeframe
        );

        let checked_payload = json!({
            "venue": input.venue,
            "canonical_symbol": input.canonical_symbol,
            "timeframe": input.timeframe,
            "source_kind": input.source_kind,
            "event_ts": input.event_ts.to_rfc3339(),
            "risk": {
                "approved": decision.approved,
                "reason": decision.reason,
                "side": decision.side,
                "requested_notional": input.requested_notional,
                "accepted_notional": decision.accepted_notional,
                "confidence": input.confidence,
                "violations": decision.violations,
                "policy": {
                    "min_confidence": policy.min_confidence,
                    "max_notional": policy.max_notional,
                    "max_drawdown_pct": policy.max_drawdown_pct,
                },
                "state": {
                    "current_exposure_notional": current_state.current_exposure_notional,
                    "equity": current_state.equity,
                    "drawdown_pct": current_state.drawdown_pct,
                    "kill_switch_enabled": current_state.kill_switch_enabled,
                }
            }
        });

        publish_event(&producer, &risk_checked_topic, &event_key, checked_payload).await?;

        if !decision.approved && !decision.violations.is_empty() {
            let violation_payload = json!({
                "venue": input.venue,
                "canonical_symbol": input.canonical_symbol,
                "timeframe": input.timeframe,
                "event_ts": input.event_ts.to_rfc3339(),
                "side": decision.side,
                "reason": decision.reason,
                "violations": decision.violations,
                "requested_notional": input.requested_notional,
                "confidence": input.confidence,
            });
            publish_event(&producer, &violation_topic, &event_key, violation_payload).await?;
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

    fn mk_input(side: &str, confidence: f64, notional: f64) -> RiskInput {
        RiskInput {
            venue: "coinbase".to_string(),
            canonical_symbol: "BTCUSD".to_string(),
            timeframe: "1m".to_string(),
            side: side.to_string(),
            confidence,
            requested_notional: notional,
            event_ts: Utc::now(),
            source_kind: "signal_scored".to_string(),
        }
    }

    fn base_state() -> RiskState {
        RiskState {
            current_exposure_notional: 0.0,
            equity: 100000.0,
            drawdown_pct: 0.5,
            kill_switch_enabled: false,
        }
    }

    fn base_policy() -> RiskPolicy {
        RiskPolicy {
            min_confidence: 0.55,
            max_notional: 100000.0,
            max_drawdown_pct: 5.0,
        }
    }

    #[test]
    fn approves_trade_within_limits() {
        let input = mk_input("buy", 0.8, 1000.0);
        let decision = evaluate_policy(&input, &base_state(), &base_policy());
        assert!(decision.approved);
        assert!(decision.violations.is_empty());
    }

    #[test]
    fn rejects_on_low_confidence() {
        let input = mk_input("buy", 0.2, 1000.0);
        let decision = evaluate_policy(&input, &base_state(), &base_policy());
        assert!(!decision.approved);
        assert!(decision
            .violations
            .iter()
            .any(|v| v == "confidence_below_threshold"));
    }

    #[test]
    fn rejects_on_notional_cap() {
        let input = mk_input("buy", 0.9, 250000.0);
        let decision = evaluate_policy(&input, &base_state(), &base_policy());
        assert!(!decision.approved);
        assert!(decision
            .violations
            .iter()
            .any(|v| v == "max_notional_exceeded"));
    }

    #[test]
    fn rejects_when_kill_switch_enabled() {
        let input = mk_input("sell", 0.9, 1000.0);
        let mut state = base_state();
        state.kill_switch_enabled = true;
        let decision = evaluate_policy(&input, &state, &base_policy());
        assert!(!decision.approved);
        assert!(decision
            .violations
            .iter()
            .any(|v| v == "kill_switch_enabled"));
    }

    #[test]
    fn parses_structure_snapshot_objective_to_side() {
        let payload = json!({
            "venue": "coinbase",
            "canonical_symbol": "BTCUSD",
            "timeframe": "1m",
            "bucket_start": "2026-04-26T00:00:00Z",
            "state": {"objective": "buy_side"}
        });

        let parsed = parse_risk_input(&payload, 1000.0).expect("must parse");
        assert_eq!(parsed.side, "buy");
        assert_eq!(parsed.source_kind, "structure_snapshot");
    }
}
