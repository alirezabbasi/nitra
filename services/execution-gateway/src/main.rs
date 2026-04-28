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
struct ExecIntent {
    venue: String,
    canonical_symbol: String,
    timeframe: String,
    approved: bool,
    side: String,
    notional: f64,
    event_ts: DateTime<Utc>,
}

#[derive(Clone, Debug)]
struct ExecConfig {
    default_order_ttl_secs: i64,
    dry_run: bool,
}

fn env_or(name: &str, default: &str) -> String {
    env::var(name).unwrap_or_else(|_| default.to_string())
}

fn env_bool_or(name: &str, default: bool) -> bool {
    env::var(name)
        .ok()
        .map(|v| {
            matches!(
                v.trim().to_ascii_lowercase().as_str(),
                "1" | "true" | "yes" | "on"
            )
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

fn parse_side(raw: &str) -> String {
    let normalized = raw.trim().to_ascii_lowercase();
    match normalized.as_str() {
        "buy" | "sell" => normalized,
        _ => "hold".to_string(),
    }
}

fn parse_exec_intent(payload: &Value) -> Option<ExecIntent> {
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

    let risk = payload.get("risk").cloned().unwrap_or(Value::Null);
    let approved = risk
        .get("approved")
        .and_then(|v| v.as_bool())
        .unwrap_or(false);
    let side = parse_side(
        risk.get("side")
            .and_then(|v| v.as_str())
            .or_else(|| payload.get("side").and_then(|v| v.as_str()))
            .unwrap_or("hold"),
    );

    let notional = risk
        .get("accepted_notional")
        .and_then(|v| v.as_f64())
        .or_else(|| risk.get("requested_notional").and_then(|v| v.as_f64()))
        .or_else(|| payload.get("notional").and_then(|v| v.as_f64()))
        .unwrap_or(0.0)
        .abs();

    let event_ts =
        parse_ts(payload.get("event_ts").and_then(|v| v.as_str())).unwrap_or_else(Utc::now);

    if venue.is_empty() || canonical_symbol.is_empty() {
        return None;
    }

    Some(ExecIntent {
        venue,
        canonical_symbol,
        timeframe,
        approved,
        side,
        notional,
        event_ts,
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

async fn ensure_execution_tables(conn: &Client) -> Result<(), tokio_postgres::Error> {
    conn.batch_execute(
        "
        CREATE TABLE IF NOT EXISTS execution_order_journal (
          order_id UUID PRIMARY KEY,
          venue TEXT NOT NULL,
          canonical_symbol TEXT NOT NULL,
          timeframe TEXT NOT NULL DEFAULT '1m',
          side TEXT NOT NULL,
          requested_notional DOUBLE PRECISION NOT NULL,
          approved BOOLEAN NOT NULL,
          status TEXT NOT NULL,
          decision_ts TIMESTAMPTZ NOT NULL,
          submitted_at TIMESTAMPTZ,
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          closed_at TIMESTAMPTZ,
          execution_metadata JSONB NOT NULL DEFAULT '{}'::jsonb
        );

        CREATE INDEX IF NOT EXISTS idx_execution_order_journal_symbol_ts
          ON execution_order_journal (venue, canonical_symbol, updated_at DESC);

        CREATE TABLE IF NOT EXISTS audit_event_log (
          audit_id UUID PRIMARY KEY,
          service_name TEXT NOT NULL,
          event_domain TEXT NOT NULL,
          event_type TEXT NOT NULL,
          correlation_id UUID,
          venue TEXT,
          canonical_symbol TEXT,
          payload JSONB NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_audit_event_log_domain_ts
          ON audit_event_log (event_domain, created_at DESC);
        ",
    )
    .await
}

async fn persist_order_journal(
    conn: &Client,
    order_id: Uuid,
    intent: &ExecIntent,
    status: &str,
    submitted_at: Option<DateTime<Utc>>,
    closed_at: Option<DateTime<Utc>>,
    execution_metadata: Value,
) -> Result<(), tokio_postgres::Error> {
    conn.execute(
        "
        INSERT INTO execution_order_journal (
          order_id, venue, canonical_symbol, timeframe, side,
          requested_notional, approved, status, decision_ts,
          submitted_at, closed_at, execution_metadata
        ) VALUES (
          $1::uuid,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12::jsonb
        )
        ON CONFLICT (order_id)
        DO UPDATE SET
          status = EXCLUDED.status,
          submitted_at = COALESCE(EXCLUDED.submitted_at, execution_order_journal.submitted_at),
          closed_at = COALESCE(EXCLUDED.closed_at, execution_order_journal.closed_at),
          execution_metadata = execution_order_journal.execution_metadata || EXCLUDED.execution_metadata,
          updated_at = now()
        ",
        &[
            &order_id,
            &intent.venue,
            &intent.canonical_symbol,
            &intent.timeframe,
            &intent.side,
            &intent.notional,
            &intent.approved,
            &status,
            &intent.event_ts,
            &submitted_at,
            &closed_at,
            &execution_metadata,
        ],
    ).await?;
    Ok(())
}

async fn insert_audit_event(
    conn: &Client,
    service_name: &str,
    event_domain: &str,
    event_type: &str,
    correlation_id: Option<Uuid>,
    venue: Option<&str>,
    canonical_symbol: Option<&str>,
    payload: Value,
) -> Result<(), tokio_postgres::Error> {
    conn.execute(
        "
        INSERT INTO audit_event_log (
          audit_id, service_name, event_domain, event_type,
          correlation_id, venue, canonical_symbol, payload
        ) VALUES ($1::uuid,$2,$3,$4,$5,$6,$7,$8::jsonb)
        ",
        &[
            &Uuid::new_v4(),
            &service_name,
            &event_domain,
            &event_type,
            &correlation_id,
            &venue,
            &canonical_symbol,
            &payload,
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
    let service_name = "execution_gateway";

    let brokers = env_or("KAFKA_BROKERS", "kafka:9092");
    let input_topic = env_or("EXECUTION_INPUT_TOPIC", "decision.risk_checked.v1");
    let order_submitted_topic = env_or("EXEC_ORDER_SUBMITTED_TOPIC", "exec.order_submitted.v1");
    let order_updated_topic = env_or("EXEC_ORDER_UPDATED_TOPIC", "exec.order_updated.v1");
    let fill_received_topic = env_or("EXEC_FILL_RECEIVED_TOPIC", "exec.fill_received.v1");
    let reconciliation_topic = env_or(
        "EXEC_RECONCILIATION_ISSUE_TOPIC",
        "exec.reconciliation_issue.v1",
    );
    let group_id = env_or("EXECUTION_GROUP_ID", "nitra-execution-gateway-v1");
    let db_dsn = env_or(
        "DATABASE_URL",
        "postgresql://trading:trading@timescaledb:5432/trading",
    );

    let exec_cfg = ExecConfig {
        default_order_ttl_secs: env_i64_or("EXEC_ORDER_TTL_SECS", 30),
        dry_run: env_bool_or("EXEC_DRY_RUN", true),
    };

    let (conn, connection) = tokio_postgres::connect(&db_dsn, NoTls).await?;
    tokio::spawn(async move {
        if let Err(e) = connection.await {
            eprintln!("postgres connection error: {e}");
        }
    });

    ensure_execution_tables(&conn).await?;

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
        let Some(intent) = parse_exec_intent(&payload) else {
            consumer.commit_message(&msg, CommitMode::Sync)?;
            continue;
        };

        let order_id = Uuid::new_v4();
        let event_key = format!(
            "{}:{}:{}",
            intent.venue, intent.canonical_symbol, intent.timeframe
        );

        let now = Utc::now();

        if !intent.approved || intent.side == "hold" || intent.notional <= 0.0 {
            let metadata = json!({
                "path": "blocked",
                "approved": intent.approved,
                "side": intent.side,
                "requested_notional": intent.notional,
            });

            persist_order_journal(
                &conn,
                order_id,
                &intent,
                "rejected_by_risk",
                None,
                Some(now),
                metadata.clone(),
            )
            .await?;

            insert_audit_event(
                &conn,
                service_name,
                "execution",
                "order_rejected",
                Some(order_id),
                Some(&intent.venue),
                Some(&intent.canonical_symbol),
                json!({
                    "timeframe": intent.timeframe,
                    "side": intent.side,
                    "requested_notional": intent.notional,
                    "approved": intent.approved,
                }),
            )
            .await?;

            publish_event(
                &producer,
                &order_updated_topic,
                &event_key,
                json!({
                    "order_id": order_id.to_string(),
                    "venue": intent.venue,
                    "canonical_symbol": intent.canonical_symbol,
                    "status": "rejected_by_risk",
                    "reason": "not_approved_or_hold",
                    "event_ts": now.to_rfc3339(),
                }),
            )
            .await?;

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

        let submit_ts = now;
        persist_order_journal(
            &conn,
            order_id,
            &intent,
            "submitted",
            Some(submit_ts),
            None,
            json!({
                "dry_run": exec_cfg.dry_run,
                "ttl_secs": exec_cfg.default_order_ttl_secs,
            }),
        )
        .await?;

        publish_event(
            &producer,
            &order_submitted_topic,
            &event_key,
            json!({
                "order_id": order_id.to_string(),
                "venue": intent.venue,
                "canonical_symbol": intent.canonical_symbol,
                "side": intent.side,
                "notional": intent.notional,
                "status": "submitted",
                "event_ts": submit_ts.to_rfc3339(),
                "dry_run": exec_cfg.dry_run,
            }),
        )
        .await?;

        insert_audit_event(
            &conn,
            service_name,
            "execution",
            "order_submitted",
            Some(order_id),
            Some(&intent.venue),
            Some(&intent.canonical_symbol),
            json!({
                "side": intent.side,
                "notional": intent.notional,
                "dry_run": exec_cfg.dry_run,
            }),
        )
        .await?;

        let fill_ts = submit_ts + chrono::Duration::seconds(1);
        persist_order_journal(
            &conn,
            order_id,
            &intent,
            "filled",
            Some(submit_ts),
            Some(fill_ts),
            json!({
                "fill_price_proxy": "market",
                "filled_notional": intent.notional,
            }),
        )
        .await?;

        publish_event(
            &producer,
            &fill_received_topic,
            &event_key,
            json!({
                "order_id": order_id.to_string(),
                "venue": intent.venue,
                "canonical_symbol": intent.canonical_symbol,
                "filled_notional": intent.notional,
                "status": "filled",
                "event_ts": fill_ts.to_rfc3339(),
            }),
        )
        .await?;

        publish_event(
            &producer,
            &order_updated_topic,
            &event_key,
            json!({
                "order_id": order_id.to_string(),
                "venue": intent.venue,
                "canonical_symbol": intent.canonical_symbol,
                "status": "filled",
                "event_ts": fill_ts.to_rfc3339(),
            }),
        )
        .await?;

        if intent.notional > 500_000.0 {
            publish_event(
                &producer,
                &reconciliation_topic,
                &event_key,
                json!({
                    "order_id": order_id.to_string(),
                    "venue": intent.venue,
                    "canonical_symbol": intent.canonical_symbol,
                    "issue": "high_notional_reconciliation_required",
                    "event_ts": fill_ts.to_rfc3339(),
                }),
            )
            .await?;

            insert_audit_event(
                &conn,
                service_name,
                "execution",
                "reconciliation_issue",
                Some(order_id),
                Some(&intent.venue),
                Some(&intent.canonical_symbol),
                json!({
                    "issue": "high_notional_reconciliation_required",
                    "notional": intent.notional,
                }),
            )
            .await?;
        }

        insert_audit_event(
            &conn,
            service_name,
            "execution",
            "order_filled",
            Some(order_id),
            Some(&intent.venue),
            Some(&intent.canonical_symbol),
            json!({
                "side": intent.side,
                "filled_notional": intent.notional,
            }),
        )
        .await?;

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

    fn mk_state(approved: bool, side: &str, notional: f64) -> Value {
        json!({
            "venue": "coinbase",
            "canonical_symbol": "BTCUSD",
            "timeframe": "1m",
            "event_ts": "2026-04-28T00:00:00Z",
            "risk": {
                "approved": approved,
                "side": side,
                "accepted_notional": notional
            }
        })
    }

    #[test]
    fn parse_approved_intent() {
        let parsed = parse_exec_intent(&mk_state(true, "buy", 1000.0)).expect("intent");
        assert!(parsed.approved);
        assert_eq!(parsed.side, "buy");
        assert_eq!(parsed.notional, 1000.0);
    }

    #[test]
    fn parse_rejected_intent() {
        let parsed = parse_exec_intent(&mk_state(false, "sell", 0.0)).expect("intent");
        assert!(!parsed.approved);
        assert_eq!(parsed.side, "sell");
    }

    #[test]
    fn side_normalization_fallback() {
        assert_eq!(parse_side("BUY"), "buy");
        assert_eq!(parse_side("unknown"), "hold");
    }
}
