use chrono::{DateTime, Utc};
use futures_util::StreamExt;
use rdkafka::consumer::{CommitMode, Consumer, StreamConsumer};
use rdkafka::message::BorrowedMessage;
use rdkafka::producer::{FutureProducer, FutureRecord};
use rdkafka::ClientConfig;
use rdkafka::Message;
use reqwest::Client as HttpClient;
use reqwest::StatusCode;
use serde_json::{json, Value};
use std::collections::{HashMap, HashSet};
use std::env;
use std::time::Duration;
use tokio::time::sleep;
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
struct ExecOrderCommand {
    order_id: Uuid,
    action: String,
    new_notional: Option<f64>,
    event_ts: DateTime<Utc>,
}

#[derive(Clone, Debug)]
struct BrokerAck {
    order_id: Uuid,
    broker_order_id: Option<String>,
    status: String,
    filled_notional: Option<f64>,
    reason: Option<String>,
    event_ts: DateTime<Utc>,
}

#[derive(Clone, Debug)]
struct AdapterResponse {
    status: String,
    broker_order_id: Option<String>,
    reason: Option<String>,
    failure_class: Option<String>,
    attempts: u32,
    terminal: bool,
}

#[derive(Clone, Debug)]
struct ExecConfig {
    default_order_ttl_secs: i64,
    dry_run: bool,
    broker_submit_url: String,
    broker_amend_url: String,
    broker_cancel_url: String,
    broker_timeout_secs: u64,
    broker_retry_max_attempts: u32,
    broker_retry_backoff_ms: u64,
    broker_retry_backoff_cap_ms: u64,
    broker_degraded_cooldown_ms: u64,
    command_stale_after_secs: i64,
    command_duplicate_window_secs: i64,
    reconciliation_sla_secs: i64,
}

#[derive(Clone, Debug)]
struct OrderJournalState {
    status: String,
    updated_at: DateTime<Utc>,
    state_version: i32,
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

fn env_u64_or(name: &str, default: u64) -> u64 {
    env::var(name)
        .ok()
        .and_then(|v| v.parse::<u64>().ok())
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

fn parse_exec_command(payload: &Value) -> Option<ExecOrderCommand> {
    let order_id = payload
        .get("order_id")
        .and_then(|v| v.as_str())
        .and_then(|v| Uuid::parse_str(v).ok())?;

    let action = payload
        .get("action")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .trim()
        .to_ascii_lowercase();

    if action != "amend" && action != "cancel" {
        return None;
    }

    let new_notional = payload.get("new_notional").and_then(|v| v.as_f64());
    let event_ts =
        parse_ts(payload.get("event_ts").and_then(|v| v.as_str())).unwrap_or_else(Utc::now);

    Some(ExecOrderCommand {
        order_id,
        action,
        new_notional,
        event_ts,
    })
}

fn parse_broker_ack(payload: &Value) -> Option<BrokerAck> {
    let order_id = payload
        .get("order_id")
        .and_then(|v| v.as_str())
        .and_then(|v| Uuid::parse_str(v).ok())?;
    let status = payload
        .get("status")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .trim()
        .to_ascii_lowercase();

    if status.is_empty() {
        return None;
    }

    Some(BrokerAck {
        order_id,
        broker_order_id: payload
            .get("broker_order_id")
            .and_then(|v| v.as_str())
            .map(|v| v.to_string()),
        status,
        filled_notional: payload.get("filled_notional").and_then(|v| v.as_f64()),
        reason: payload
            .get("reason")
            .and_then(|v| v.as_str())
            .map(|v| v.to_string()),
        event_ts: parse_ts(payload.get("event_ts").and_then(|v| v.as_str()))
            .unwrap_or_else(Utc::now),
    })
}

fn classify_reqwest_error(err: &reqwest::Error) -> (String, bool) {
    let msg = err.to_string().to_ascii_lowercase();
    if err.is_connect() {
        if msg.contains("dns")
            || msg.contains("failed to lookup")
            || msg.contains("name resolution")
            || msg.contains("name or service not known")
            || msg.contains("temporary failure in name resolution")
        {
            return ("dns_resolution".to_string(), true);
        }
        if err.is_timeout() {
            return ("connect_timeout".to_string(), true);
        }
        return ("connect_error".to_string(), true);
    }
    if err.is_timeout() {
        return ("io_timeout".to_string(), true);
    }
    ("request_error".to_string(), false)
}

fn classify_http_status(status: StatusCode) -> (String, bool) {
    if status.is_server_error() {
        return ("upstream_5xx".to_string(), true);
    }
    if status.is_client_error() {
        return ("upstream_4xx".to_string(), false);
    }
    ("upstream_status_other".to_string(), false)
}

fn attempt_backoff_ms(cfg: &ExecConfig, attempt: u32) -> u64 {
    let base = cfg.broker_retry_backoff_ms.max(1);
    let capped_shift = attempt.saturating_sub(1).min(12);
    let mult = 1u64 << capped_shift;
    (base.saturating_mul(mult)).min(cfg.broker_retry_backoff_cap_ms.max(base))
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

        ALTER TABLE execution_order_journal
          ADD COLUMN IF NOT EXISTS broker_order_id TEXT;

        ALTER TABLE execution_order_journal
          ADD COLUMN IF NOT EXISTS state_version INT NOT NULL DEFAULT 0;

        CREATE UNIQUE INDEX IF NOT EXISTS uq_execution_order_journal_broker_order_id
          ON execution_order_journal (broker_order_id)
          WHERE broker_order_id IS NOT NULL;

        CREATE INDEX IF NOT EXISTS idx_execution_order_journal_symbol_ts
          ON execution_order_journal (venue, canonical_symbol, updated_at DESC);

        CREATE TABLE IF NOT EXISTS execution_command_log (
          command_id UUID PRIMARY KEY,
          order_id UUID NOT NULL,
          action TEXT NOT NULL,
          accepted BOOLEAN NOT NULL,
          reason TEXT,
          payload JSONB NOT NULL DEFAULT '{}'::jsonb,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_execution_command_log_order_ts
          ON execution_command_log (order_id, created_at DESC);

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
    broker_order_id: Option<&str>,
    execution_metadata: Value,
) -> Result<(), tokio_postgres::Error> {
    conn.execute(
        "
        INSERT INTO execution_order_journal (
          order_id, venue, canonical_symbol, timeframe, side,
          requested_notional, approved, status, decision_ts,
          submitted_at, closed_at, broker_order_id, execution_metadata, state_version
        ) VALUES (
          $1::uuid,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13::jsonb,1
        )
        ON CONFLICT (order_id)
        DO UPDATE SET
          status = EXCLUDED.status,
          submitted_at = COALESCE(EXCLUDED.submitted_at, execution_order_journal.submitted_at),
          closed_at = COALESCE(EXCLUDED.closed_at, execution_order_journal.closed_at),
          broker_order_id = COALESCE(EXCLUDED.broker_order_id, execution_order_journal.broker_order_id),
          execution_metadata = execution_order_journal.execution_metadata || EXCLUDED.execution_metadata,
          state_version = execution_order_journal.state_version + 1,
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
            &broker_order_id,
            &execution_metadata,
        ],
    )
    .await?;
    Ok(())
}

async fn update_order_journal_from_ack(
    conn: &Client,
    ack: &BrokerAck,
) -> Result<Option<(String, String, String)>, tokio_postgres::Error> {
    let row = conn
        .query_opt(
            "
            UPDATE execution_order_journal
            SET
              status = $2,
              broker_order_id = COALESCE($3, broker_order_id),
              closed_at = CASE WHEN $2 IN ('filled','rejected','cancelled') THEN COALESCE(closed_at, $4) ELSE closed_at END,
              execution_metadata = execution_metadata || $5::jsonb,
              state_version = state_version + 1,
              updated_at = now()
            WHERE order_id = $1::uuid
            RETURNING venue, canonical_symbol, timeframe
            ",
            &[
                &ack.order_id,
                &ack.status,
                &ack.broker_order_id,
                &ack.event_ts,
                &json!({
                    "ack_status": ack.status,
                    "ack_reason": ack.reason,
                    "filled_notional": ack.filled_notional,
                    "ack_event_ts": ack.event_ts.to_rfc3339(),
                }),
            ],
        )
        .await?;

    Ok(row.map(|r| {
        (
            r.get::<_, String>(0),
            r.get::<_, String>(1),
            r.get::<_, String>(2),
        )
    }))
}

async fn load_order_intent(
    conn: &Client,
    order_id: Uuid,
) -> Result<Option<ExecIntent>, tokio_postgres::Error> {
    let row = conn
        .query_opt(
            "
            SELECT venue, canonical_symbol, timeframe, approved, side, requested_notional, decision_ts
            FROM execution_order_journal
            WHERE order_id = $1::uuid
            ",
            &[&order_id],
        )
        .await?;

    Ok(row.map(|r| ExecIntent {
        venue: r.get::<_, String>(0),
        canonical_symbol: r.get::<_, String>(1),
        timeframe: r.get::<_, String>(2),
        approved: r.get::<_, bool>(3),
        side: r.get::<_, String>(4),
        notional: r.get::<_, f64>(5),
        event_ts: r.get::<_, DateTime<Utc>>(6),
    }))
}

async fn load_order_state(
    conn: &Client,
    order_id: Uuid,
) -> Result<Option<OrderJournalState>, tokio_postgres::Error> {
    let row = conn
        .query_opt(
            "
            SELECT status, updated_at, state_version
            FROM execution_order_journal
            WHERE order_id = $1::uuid
            ",
            &[&order_id],
        )
        .await?;

    Ok(row.map(|r| OrderJournalState {
        status: r.get::<_, String>(0),
        updated_at: r.get::<_, DateTime<Utc>>(1),
        state_version: r.get::<_, i32>(2),
    }))
}

async fn is_duplicate_command(
    conn: &Client,
    command: &ExecOrderCommand,
    window_secs: i64,
) -> Result<bool, tokio_postgres::Error> {
    let row = conn
        .query_opt(
            "
            SELECT 1
            FROM execution_command_log
            WHERE order_id = $1::uuid
              AND action = $2
              AND payload->>'new_notional' IS NOT DISTINCT FROM $3
              AND created_at >= now() - ($4::text || ' seconds')::interval
            LIMIT 1
            ",
            &[
                &command.order_id,
                &command.action,
                &command.new_notional.map(|v| v.to_string()),
                &window_secs,
            ],
        )
        .await?;
    Ok(row.is_some())
}

fn is_valid_lifecycle_transition(current: &str, next: &str) -> bool {
    let mut map: HashMap<&str, HashSet<&str>> = HashMap::new();
    map.insert(
        "submitted",
        HashSet::from([
            "filled",
            "rejected",
            "cancelled",
            "amend_requested",
            "cancel_requested",
        ]),
    );
    map.insert(
        "amend_requested",
        HashSet::from(["submitted", "filled", "rejected", "cancelled"]),
    );
    map.insert(
        "cancel_requested",
        HashSet::from(["cancelled", "filled", "rejected"]),
    );
    map.insert("rejected_by_risk", HashSet::new());
    map.insert("rejected_by_broker", HashSet::new());
    map.insert("filled", HashSet::new());
    map.insert("rejected", HashSet::new());
    map.insert("cancelled", HashSet::new());
    map.get(current).map(|v| v.contains(next)).unwrap_or(false)
}

async fn insert_command_log(
    conn: &Client,
    command: &ExecOrderCommand,
    accepted: bool,
    reason: Option<&str>,
    payload: Value,
) -> Result<(), tokio_postgres::Error> {
    conn.execute(
        "
        INSERT INTO execution_command_log (
          command_id, order_id, action, accepted, reason, payload
        ) VALUES ($1::uuid,$2::uuid,$3,$4,$5,$6::jsonb)
        ",
        &[
            &Uuid::new_v4(),
            &command.order_id,
            &command.action,
            &accepted,
            &reason,
            &payload,
        ],
    )
    .await?;
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

async fn adapter_submit(
    http: &HttpClient,
    cfg: &ExecConfig,
    order_id: Uuid,
    intent: &ExecIntent,
) -> AdapterResponse {
    if cfg.dry_run {
        return AdapterResponse {
            status: "submitted".to_string(),
            broker_order_id: Some(format!("dry-{}", order_id)),
            reason: None,
            failure_class: None,
            attempts: 1,
            terminal: false,
        };
    }

    let req = json!({
        "order_id": order_id.to_string(),
        "venue": intent.venue,
        "symbol": intent.canonical_symbol,
        "side": intent.side,
        "notional": intent.notional,
        "timeframe": intent.timeframe,
    });

    let max_attempts = cfg.broker_retry_max_attempts.max(1);
    for attempt in 1..=max_attempts {
        match http.post(&cfg.broker_submit_url).json(&req).send().await {
            Ok(resp) if resp.status().is_success() => {
                let parsed = resp.json::<Value>().await.unwrap_or_else(|_| json!({}));
                return AdapterResponse {
                    status: parsed
                        .get("status")
                        .and_then(|v| v.as_str())
                        .unwrap_or("submitted")
                        .to_ascii_lowercase(),
                    broker_order_id: parsed
                        .get("broker_order_id")
                        .and_then(|v| v.as_str())
                        .map(|v| v.to_string()),
                    reason: parsed
                        .get("reason")
                        .and_then(|v| v.as_str())
                        .map(|v| v.to_string()),
                    failure_class: None,
                    attempts: attempt,
                    terminal: false,
                };
            }
            Ok(resp) => {
                let status = resp.status();
                let (failure_class, retryable) = classify_http_status(status);
                if retryable && attempt < max_attempts {
                    sleep(Duration::from_millis(attempt_backoff_ms(cfg, attempt))).await;
                    continue;
                }
                if attempt >= max_attempts && cfg.broker_degraded_cooldown_ms > 0 {
                    sleep(Duration::from_millis(cfg.broker_degraded_cooldown_ms)).await;
                }
                return AdapterResponse {
                    status: "rejected".to_string(),
                    broker_order_id: None,
                    reason: Some(format!("submit_http_status_{}", status)),
                    failure_class: Some(failure_class),
                    attempts: attempt,
                    terminal: true,
                };
            }
            Err(e) => {
                let (failure_class, retryable) = classify_reqwest_error(&e);
                if retryable && attempt < max_attempts {
                    sleep(Duration::from_millis(attempt_backoff_ms(cfg, attempt))).await;
                    continue;
                }
                if attempt >= max_attempts && cfg.broker_degraded_cooldown_ms > 0 {
                    sleep(Duration::from_millis(cfg.broker_degraded_cooldown_ms)).await;
                }
                return AdapterResponse {
                    status: "rejected".to_string(),
                    broker_order_id: None,
                    reason: Some(format!("submit_error: {}", e)),
                    failure_class: Some(failure_class),
                    attempts: attempt,
                    terminal: true,
                };
            }
        }
    }
    AdapterResponse {
        status: "rejected".to_string(),
        broker_order_id: None,
        reason: Some("submit_unknown_terminal".to_string()),
        failure_class: Some("unknown".to_string()),
        attempts: max_attempts,
        terminal: true,
    }
}

async fn adapter_amend(
    http: &HttpClient,
    cfg: &ExecConfig,
    command: &ExecOrderCommand,
) -> AdapterResponse {
    if cfg.dry_run {
        return AdapterResponse {
            status: "amend_requested".to_string(),
            broker_order_id: None,
            reason: None,
            failure_class: None,
            attempts: 1,
            terminal: false,
        };
    }

    let req = json!({
        "order_id": command.order_id.to_string(),
        "new_notional": command.new_notional,
    });

    let max_attempts = cfg.broker_retry_max_attempts.max(1);
    for attempt in 1..=max_attempts {
        match http.post(&cfg.broker_amend_url).json(&req).send().await {
            Ok(resp) if resp.status().is_success() => {
                return AdapterResponse {
                    status: "amend_requested".to_string(),
                    broker_order_id: None,
                    reason: None,
                    failure_class: None,
                    attempts: attempt,
                    terminal: false,
                }
            }
            Ok(resp) => {
                let status = resp.status();
                let (failure_class, retryable) = classify_http_status(status);
                if retryable && attempt < max_attempts {
                    sleep(Duration::from_millis(attempt_backoff_ms(cfg, attempt))).await;
                    continue;
                }
                if attempt >= max_attempts && cfg.broker_degraded_cooldown_ms > 0 {
                    sleep(Duration::from_millis(cfg.broker_degraded_cooldown_ms)).await;
                }
                return AdapterResponse {
                    status: "amend_rejected".to_string(),
                    broker_order_id: None,
                    reason: Some(format!("amend_http_status_{}", status)),
                    failure_class: Some(failure_class),
                    attempts: attempt,
                    terminal: true,
                };
            }
            Err(e) => {
                let (failure_class, retryable) = classify_reqwest_error(&e);
                if retryable && attempt < max_attempts {
                    sleep(Duration::from_millis(attempt_backoff_ms(cfg, attempt))).await;
                    continue;
                }
                if attempt >= max_attempts && cfg.broker_degraded_cooldown_ms > 0 {
                    sleep(Duration::from_millis(cfg.broker_degraded_cooldown_ms)).await;
                }
                return AdapterResponse {
                    status: "amend_rejected".to_string(),
                    broker_order_id: None,
                    reason: Some(format!("amend_error: {}", e)),
                    failure_class: Some(failure_class),
                    attempts: attempt,
                    terminal: true,
                };
            }
        }
    }
    AdapterResponse {
        status: "amend_rejected".to_string(),
        broker_order_id: None,
        reason: Some("amend_unknown_terminal".to_string()),
        failure_class: Some("unknown".to_string()),
        attempts: max_attempts,
        terminal: true,
    }
}

async fn adapter_cancel(
    http: &HttpClient,
    cfg: &ExecConfig,
    command: &ExecOrderCommand,
) -> AdapterResponse {
    if cfg.dry_run {
        return AdapterResponse {
            status: "cancel_requested".to_string(),
            broker_order_id: None,
            reason: None,
            failure_class: None,
            attempts: 1,
            terminal: false,
        };
    }

    let req = json!({
        "order_id": command.order_id.to_string(),
    });

    let max_attempts = cfg.broker_retry_max_attempts.max(1);
    for attempt in 1..=max_attempts {
        match http.post(&cfg.broker_cancel_url).json(&req).send().await {
            Ok(resp) if resp.status().is_success() => {
                return AdapterResponse {
                    status: "cancel_requested".to_string(),
                    broker_order_id: None,
                    reason: None,
                    failure_class: None,
                    attempts: attempt,
                    terminal: false,
                }
            }
            Ok(resp) => {
                let status = resp.status();
                let (failure_class, retryable) = classify_http_status(status);
                if retryable && attempt < max_attempts {
                    sleep(Duration::from_millis(attempt_backoff_ms(cfg, attempt))).await;
                    continue;
                }
                if attempt >= max_attempts && cfg.broker_degraded_cooldown_ms > 0 {
                    sleep(Duration::from_millis(cfg.broker_degraded_cooldown_ms)).await;
                }
                return AdapterResponse {
                    status: "cancel_rejected".to_string(),
                    broker_order_id: None,
                    reason: Some(format!("cancel_http_status_{}", status)),
                    failure_class: Some(failure_class),
                    attempts: attempt,
                    terminal: true,
                };
            }
            Err(e) => {
                let (failure_class, retryable) = classify_reqwest_error(&e);
                if retryable && attempt < max_attempts {
                    sleep(Duration::from_millis(attempt_backoff_ms(cfg, attempt))).await;
                    continue;
                }
                if attempt >= max_attempts && cfg.broker_degraded_cooldown_ms > 0 {
                    sleep(Duration::from_millis(cfg.broker_degraded_cooldown_ms)).await;
                }
                return AdapterResponse {
                    status: "cancel_rejected".to_string(),
                    broker_order_id: None,
                    reason: Some(format!("cancel_error: {}", e)),
                    failure_class: Some(failure_class),
                    attempts: attempt,
                    terminal: true,
                };
            }
        }
    }
    AdapterResponse {
        status: "cancel_rejected".to_string(),
        broker_order_id: None,
        reason: Some("cancel_unknown_terminal".to_string()),
        failure_class: Some("unknown".to_string()),
        attempts: max_attempts,
        terminal: true,
    }
}

async fn handle_intent(
    conn: &Client,
    producer: &FutureProducer,
    http: &HttpClient,
    cfg: &ExecConfig,
    service_name: &str,
    order_submitted_topic: &str,
    order_updated_topic: &str,
    fill_received_topic: &str,
    reconciliation_topic: &str,
    intent: ExecIntent,
) -> Result<(), Box<dyn std::error::Error>> {
    let order_id = Uuid::new_v4();
    let event_key = format!(
        "{}:{}:{}",
        intent.venue, intent.canonical_symbol, intent.timeframe
    );
    let now = Utc::now();

    if !intent.approved || intent.side == "hold" || intent.notional <= 0.0 {
        persist_order_journal(
            conn,
            order_id,
            &intent,
            "rejected_by_risk",
            None,
            Some(now),
            None,
            json!({"path": "blocked"}),
        )
        .await?;

        insert_audit_event(
            conn,
            service_name,
            "execution",
            "order_rejected",
            Some(order_id),
            Some(&intent.venue),
            Some(&intent.canonical_symbol),
            json!({"reason": "not_approved_or_hold", "notional": intent.notional}),
        )
        .await?;

        publish_event(
            producer,
            order_updated_topic,
            &event_key,
            json!({
                "order_id": order_id.to_string(),
                "venue": intent.venue,
                "canonical_symbol": intent.canonical_symbol,
                "status": "rejected_by_risk",
                "event_ts": now.to_rfc3339(),
            }),
        )
        .await?;

        return Ok(());
    }

    let submit_response = adapter_submit(http, cfg, order_id, &intent).await;
    let submit_status = submit_response.status.clone();
    let is_submitted = submit_status == "submitted" || submit_status == "accepted";

    persist_order_journal(
        conn,
        order_id,
        &intent,
        if is_submitted {
            "submitted"
        } else {
            "rejected_by_broker"
        },
        Some(now),
        if is_submitted { None } else { Some(now) },
        submit_response.broker_order_id.as_deref(),
        json!({
            "adapter_status": submit_status,
            "adapter_reason": submit_response.reason,
            "adapter_failure_class": submit_response.failure_class,
            "adapter_attempts": submit_response.attempts,
            "adapter_terminal": submit_response.terminal,
            "dry_run": cfg.dry_run,
            "ttl_secs": cfg.default_order_ttl_secs,
        }),
    )
    .await?;

    publish_event(
        producer,
        order_submitted_topic,
        &event_key,
        json!({
            "order_id": order_id.to_string(),
            "venue": intent.venue,
            "canonical_symbol": intent.canonical_symbol,
            "side": intent.side,
            "notional": intent.notional,
            "status": if is_submitted { "submitted" } else { "rejected_by_broker" },
            "broker_order_id": submit_response.broker_order_id,
            "reason": submit_response.reason,
            "failure_class": submit_response.failure_class,
            "attempts": submit_response.attempts,
            "event_ts": now.to_rfc3339(),
        }),
    )
    .await?;

    insert_audit_event(
        conn,
        service_name,
        "execution",
        if is_submitted {
            "order_submitted"
        } else {
            "order_submit_rejected"
        },
        Some(order_id),
        Some(&intent.venue),
        Some(&intent.canonical_symbol),
        json!({
            "side": intent.side,
            "notional": intent.notional,
            "broker_order_id": submit_response.broker_order_id,
            "reason": submit_response.reason,
            "failure_class": submit_response.failure_class,
            "attempts": submit_response.attempts,
        }),
    )
    .await?;

    if !is_submitted {
        if let Some(failure_class) = submit_response.failure_class.clone() {
            publish_event(
                producer,
                reconciliation_topic,
                &event_key,
                json!({
                    "order_id": order_id.to_string(),
                    "venue": intent.venue,
                    "canonical_symbol": intent.canonical_symbol,
                    "issue": "adapter_terminal_failure",
                    "failure_class": failure_class,
                    "reason": submit_response.reason,
                    "attempts": submit_response.attempts,
                    "event_ts": now.to_rfc3339(),
                }),
            )
            .await?;
        }
    }
    if is_submitted {
        let age_secs = (now - intent.event_ts).num_seconds().max(0);
        if age_secs > cfg.reconciliation_sla_secs {
            publish_event(
                producer,
                reconciliation_topic,
                &event_key,
                json!({
                    "order_id": order_id.to_string(),
                    "venue": intent.venue,
                    "canonical_symbol": intent.canonical_symbol,
                    "issue": "reconciliation_sla_breach",
                    "sla_seconds": cfg.reconciliation_sla_secs,
                    "age_seconds": age_secs,
                    "event_ts": now.to_rfc3339(),
                }),
            )
            .await?;
        }
    }

    if cfg.dry_run && is_submitted {
        let fill_ts = now + chrono::Duration::seconds(1);
        persist_order_journal(
            conn,
            order_id,
            &intent,
            "filled",
            Some(now),
            Some(fill_ts),
            Some(&format!("dry-{}", order_id)),
            json!({"filled_notional": intent.notional}),
        )
        .await?;

        publish_event(
            producer,
            fill_received_topic,
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
            producer,
            order_updated_topic,
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
                producer,
                reconciliation_topic,
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
        }
    }

    Ok(())
}

async fn handle_order_command(
    conn: &Client,
    producer: &FutureProducer,
    http: &HttpClient,
    cfg: &ExecConfig,
    service_name: &str,
    order_updated_topic: &str,
    reconciliation_topic: &str,
    command: ExecOrderCommand,
) -> Result<(), Box<dyn std::error::Error>> {
    let Some(intent) = load_order_intent(conn, command.order_id).await? else {
        insert_command_log(conn, &command, false, Some("unknown_order_id"), json!({})).await?;
        return Ok(());
    };
    let Some(state) = load_order_state(conn, command.order_id).await? else {
        insert_command_log(conn, &command, false, Some("missing_order_state"), json!({})).await?;
        return Ok(());
    };

    if command.event_ts
        < state.updated_at - chrono::Duration::seconds(cfg.command_stale_after_secs.max(0))
    {
        insert_command_log(
            conn,
            &command,
            false,
            Some("stale_command"),
            json!({"state_status": state.status, "state_version": state.state_version}),
        )
        .await?;
        return Ok(());
    }

    if is_duplicate_command(conn, &command, cfg.command_duplicate_window_secs.max(1)).await? {
        insert_command_log(
            conn,
            &command,
            false,
            Some("duplicate_command"),
            json!({"state_status": state.status, "state_version": state.state_version}),
        )
        .await?;
        return Ok(());
    }

    let response = if command.action == "amend" {
        adapter_amend(http, cfg, &command).await
    } else {
        adapter_cancel(http, cfg, &command).await
    };

    let accepted = response.status.ends_with("requested") || response.status == "accepted";
    insert_command_log(
        conn,
        &command,
        accepted,
        response.reason.as_deref(),
        json!({
            "action": command.action,
            "new_notional": command.new_notional,
            "status": response.status,
            "failure_class": response.failure_class,
            "attempts": response.attempts,
        }),
    )
    .await?;

    if accepted {
        let journal_status = if command.action == "cancel" {
            "cancel_requested"
        } else {
            "amend_requested"
        };
        if !is_valid_lifecycle_transition(&state.status, journal_status) {
            insert_command_log(
                conn,
                &command,
                false,
                Some("invalid_lifecycle_transition"),
                json!({"from_status": state.status, "to_status": journal_status, "state_version": state.state_version}),
            )
            .await?;
            return Ok(());
        }

        persist_order_journal(
            conn,
            command.order_id,
            &intent,
            journal_status,
            None,
            None,
            None,
            json!({
                "last_command_action": command.action,
                "last_command_event_ts": command.event_ts.to_rfc3339(),
                "command_new_notional": command.new_notional,
            }),
        )
        .await?;
    }

    let event_key = format!(
        "{}:{}:{}",
        intent.venue, intent.canonical_symbol, intent.timeframe
    );
    publish_event(
        producer,
        order_updated_topic,
        &event_key,
        json!({
            "order_id": command.order_id.to_string(),
            "venue": intent.venue,
            "canonical_symbol": intent.canonical_symbol,
            "status": response.status,
            "action": command.action,
            "event_ts": command.event_ts.to_rfc3339(),
            "reason": response.reason,
            "failure_class": response.failure_class,
            "attempts": response.attempts,
        }),
    )
    .await?;

    insert_audit_event(
        conn,
        service_name,
        "execution",
        "order_command",
        Some(command.order_id),
        Some(&intent.venue),
        Some(&intent.canonical_symbol),
        json!({
            "action": command.action,
            "accepted": accepted,
            "reason": response.reason,
            "new_notional": command.new_notional,
            "failure_class": response.failure_class,
            "attempts": response.attempts,
        }),
    )
    .await?;

    if !accepted {
        if let Some(failure_class) = response.failure_class.clone() {
            publish_event(
                producer,
                reconciliation_topic,
                &event_key,
                json!({
                    "order_id": command.order_id.to_string(),
                    "venue": intent.venue,
                    "canonical_symbol": intent.canonical_symbol,
                    "issue": "adapter_command_failure",
                    "action": command.action,
                    "failure_class": failure_class,
                    "reason": response.reason,
                    "attempts": response.attempts,
                    "event_ts": command.event_ts.to_rfc3339(),
                }),
            )
            .await?;
        }
    }

    Ok(())
}

async fn handle_broker_ack(
    conn: &Client,
    producer: &FutureProducer,
    cfg: &ExecConfig,
    service_name: &str,
    order_updated_topic: &str,
    fill_received_topic: &str,
    reconciliation_topic: &str,
    ack: BrokerAck,
) -> Result<(), Box<dyn std::error::Error>> {
    let Some(state) = load_order_state(conn, ack.order_id).await? else {
        insert_audit_event(
            conn,
            service_name,
            "execution",
            "orphan_broker_ack",
            Some(ack.order_id),
            None,
            None,
            json!({
                "status": ack.status,
                "broker_order_id": ack.broker_order_id,
                "reason": ack.reason,
            }),
        )
        .await?;
        return Ok(());
    };
    if !is_valid_lifecycle_transition(&state.status, &ack.status) {
        insert_audit_event(
            conn,
            service_name,
            "execution",
            "invalid_lifecycle_transition",
            Some(ack.order_id),
            None,
            None,
            json!({"from_status": state.status, "to_status": ack.status, "state_version": state.state_version}),
        )
        .await?;
        return Ok(());
    }

    let Some((venue, symbol, timeframe)) = update_order_journal_from_ack(conn, &ack).await? else {
        return Ok(());
    };

    let event_key = format!("{}:{}:{}", venue, symbol, timeframe);

    publish_event(
        producer,
        order_updated_topic,
        &event_key,
        json!({
            "order_id": ack.order_id.to_string(),
            "venue": venue,
            "canonical_symbol": symbol,
            "status": ack.status,
            "broker_order_id": ack.broker_order_id,
            "reason": ack.reason,
            "event_ts": ack.event_ts.to_rfc3339(),
        }),
    )
    .await?;

    if ack.status == "filled" {
        publish_event(
            producer,
            fill_received_topic,
            &event_key,
            json!({
                "order_id": ack.order_id.to_string(),
                "venue": venue,
                "canonical_symbol": symbol,
                "status": "filled",
                "filled_notional": ack.filled_notional,
                "broker_order_id": ack.broker_order_id,
                "event_ts": ack.event_ts.to_rfc3339(),
            }),
        )
        .await?;
    }

    if ack.status == "rejected" || ack.status == "cancelled" {
        let age_secs = (ack.event_ts - state.updated_at).num_seconds().max(0);
        publish_event(
            producer,
            reconciliation_topic,
            &event_key,
            json!({
                "order_id": ack.order_id.to_string(),
                "venue": venue,
                "canonical_symbol": symbol,
                "issue": "broker_terminal_status",
                "status": ack.status,
                "reason": ack.reason,
                "sla_seconds": cfg.reconciliation_sla_secs,
                "age_seconds": age_secs,
                "event_ts": ack.event_ts.to_rfc3339(),
            }),
        )
        .await?;
    }

    insert_audit_event(
        conn,
        service_name,
        "execution",
        "broker_ack",
        Some(ack.order_id),
        Some(&venue),
        Some(&symbol),
        json!({
            "status": ack.status,
            "broker_order_id": ack.broker_order_id,
            "reason": ack.reason,
            "filled_notional": ack.filled_notional,
        }),
    )
    .await?;

    Ok(())
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let service_name = "execution_gateway";

    let brokers = env_or("KAFKA_BROKERS", "kafka:9092");
    let intent_topic = env_or("EXECUTION_INPUT_TOPIC", "decision.risk_checked.v1");
    let command_topic = env_or("EXECUTION_COMMAND_TOPIC", "exec.order_command.v1");
    let broker_ack_topic = env_or("EXECUTION_BROKER_ACK_TOPIC", "broker.execution.ack.v1");

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
        broker_submit_url: env_or(
            "EXEC_BROKER_SUBMIT_URL",
            "http://localhost:18080/orders/submit",
        ),
        broker_amend_url: env_or(
            "EXEC_BROKER_AMEND_URL",
            "http://localhost:18080/orders/amend",
        ),
        broker_cancel_url: env_or(
            "EXEC_BROKER_CANCEL_URL",
            "http://localhost:18080/orders/cancel",
        ),
        broker_timeout_secs: env_u64_or("EXEC_BROKER_TIMEOUT_SECS", 5),
        broker_retry_max_attempts: env_u64_or("EXEC_BROKER_RETRY_MAX_ATTEMPTS", 3) as u32,
        broker_retry_backoff_ms: env_u64_or("EXEC_BROKER_RETRY_BACKOFF_MS", 200),
        broker_retry_backoff_cap_ms: env_u64_or("EXEC_BROKER_RETRY_BACKOFF_CAP_MS", 2000),
        broker_degraded_cooldown_ms: env_u64_or("EXEC_BROKER_DEGRADED_COOLDOWN_MS", 250),
        command_stale_after_secs: env_i64_or("EXEC_COMMAND_STALE_AFTER_SECS", 120),
        command_duplicate_window_secs: env_i64_or("EXEC_COMMAND_DUPLICATE_WINDOW_SECS", 300),
        reconciliation_sla_secs: env_i64_or("EXEC_RECONCILIATION_SLA_SECS", 180),
    };

    let http = HttpClient::builder()
        .timeout(Duration::from_secs(exec_cfg.broker_timeout_secs.max(1)))
        .build()?;

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
    consumer.subscribe(&[&intent_topic, &command_topic, &broker_ack_topic])?;

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

        let result = if source_topic == intent_topic {
            if let Some(intent) = parse_exec_intent(&payload) {
                handle_intent(
                    &conn,
                    &producer,
                    &http,
                    &exec_cfg,
                    service_name,
                    &order_submitted_topic,
                    &order_updated_topic,
                    &fill_received_topic,
                    &reconciliation_topic,
                    intent,
                )
                .await
            } else {
                Ok(())
            }
        } else if source_topic == command_topic {
            if let Some(command) = parse_exec_command(&payload) {
                handle_order_command(
                    &conn,
                    &producer,
                    &http,
                    &exec_cfg,
                    service_name,
                    &order_updated_topic,
                    &reconciliation_topic,
                    command,
                )
                .await
            } else {
                Ok(())
            }
        } else if source_topic == broker_ack_topic {
            if let Some(ack) = parse_broker_ack(&payload) {
                handle_broker_ack(
                    &conn,
                    &producer,
                    &exec_cfg,
                    service_name,
                    &order_updated_topic,
                    &fill_received_topic,
                    &reconciliation_topic,
                    ack,
                )
                .await
            } else {
                Ok(())
            }
        } else {
            Ok(())
        };

        if let Err(e) = result {
            eprintln!("execution message handling error on topic {source_topic}: {e}");
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
    fn parse_command_and_ack() {
        let cmd = parse_exec_command(&json!({
            "order_id": Uuid::nil().to_string(),
            "action": "amend",
            "new_notional": 1234.0,
            "event_ts": "2026-04-28T00:00:00Z"
        }))
        .expect("cmd");
        assert_eq!(cmd.action, "amend");

        let ack = parse_broker_ack(&json!({
            "order_id": Uuid::nil().to_string(),
            "status": "filled",
            "filled_notional": 1234.0,
            "event_ts": "2026-04-28T00:00:01Z"
        }))
        .expect("ack");
        assert_eq!(ack.status, "filled");
    }

    #[test]
    fn classify_http_status_retryability() {
        let (c1, r1) = classify_http_status(StatusCode::INTERNAL_SERVER_ERROR);
        assert_eq!(c1, "upstream_5xx");
        assert!(r1);
        let (c2, r2) = classify_http_status(StatusCode::BAD_REQUEST);
        assert_eq!(c2, "upstream_4xx");
        assert!(!r2);
    }

    #[test]
    fn backoff_is_bounded() {
        let cfg = ExecConfig {
            default_order_ttl_secs: 30,
            dry_run: false,
            broker_submit_url: "http://x".to_string(),
            broker_amend_url: "http://x".to_string(),
            broker_cancel_url: "http://x".to_string(),
            broker_timeout_secs: 5,
            broker_retry_max_attempts: 5,
            broker_retry_backoff_ms: 100,
            broker_retry_backoff_cap_ms: 250,
            broker_degraded_cooldown_ms: 10,
            command_stale_after_secs: 120,
            command_duplicate_window_secs: 300,
            reconciliation_sla_secs: 180,
        };
        assert_eq!(attempt_backoff_ms(&cfg, 1), 100);
        assert_eq!(attempt_backoff_ms(&cfg, 2), 200);
        assert_eq!(attempt_backoff_ms(&cfg, 3), 250);
        assert_eq!(attempt_backoff_ms(&cfg, 5), 250);
    }

    #[test]
    fn lifecycle_transition_guard_blocks_invalid_paths() {
        assert!(is_valid_lifecycle_transition("submitted", "filled"));
        assert!(is_valid_lifecycle_transition("submitted", "cancel_requested"));
        assert!(!is_valid_lifecycle_transition("filled", "submitted"));
        assert!(!is_valid_lifecycle_transition("cancelled", "amend_requested"));
    }
}
