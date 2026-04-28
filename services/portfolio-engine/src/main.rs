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
struct FillEvent {
    order_id: Uuid,
    venue: String,
    canonical_symbol: String,
    timeframe: String,
    filled_notional: f64,
    event_ts: DateTime<Utc>,
}

#[derive(Clone, Debug)]
struct PortfolioConfig {
    account_id: String,
    default_equity: f64,
}

#[derive(Clone, Debug)]
struct JournalOrder {
    side: String,
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

fn message_payload_json(msg: &BorrowedMessage<'_>) -> Option<Value> {
    let payload = msg.payload_view::<str>()?.ok()?;
    serde_json::from_str::<Value>(payload).ok()
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

fn parse_fill(payload: &Value) -> Option<FillEvent> {
    let order_id = payload
        .get("order_id")
        .and_then(|v| v.as_str())
        .and_then(|s| Uuid::parse_str(s).ok())?;

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
    let filled_notional = payload.get("filled_notional").and_then(|v| v.as_f64())?;
    let event_ts =
        parse_ts(payload.get("event_ts").and_then(|v| v.as_str())).unwrap_or_else(Utc::now);

    if filled_notional <= 0.0 {
        return None;
    }

    Some(FillEvent {
        order_id,
        venue,
        canonical_symbol,
        timeframe,
        filled_notional: filled_notional.abs(),
        event_ts,
    })
}

async fn ensure_portfolio_tables(conn: &Client) -> Result<(), tokio_postgres::Error> {
    conn.batch_execute(
        "
        CREATE TABLE IF NOT EXISTS portfolio_position_state (
          account_id TEXT NOT NULL,
          venue TEXT NOT NULL,
          canonical_symbol TEXT NOT NULL,
          timeframe TEXT NOT NULL DEFAULT '1m',
          net_position_notional DOUBLE PRECISION NOT NULL DEFAULT 0,
          gross_exposure_notional DOUBLE PRECISION NOT NULL DEFAULT 0,
          last_order_id UUID,
          last_fill_notional DOUBLE PRECISION NOT NULL DEFAULT 0,
          last_fill_side TEXT,
          last_fill_ts TIMESTAMPTZ,
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          PRIMARY KEY (account_id, venue, canonical_symbol, timeframe)
        );

        CREATE INDEX IF NOT EXISTS idx_portfolio_position_state_updated
          ON portfolio_position_state (updated_at DESC);

        CREATE TABLE IF NOT EXISTS portfolio_account_state (
          account_id TEXT PRIMARY KEY,
          equity DOUBLE PRECISION NOT NULL DEFAULT 100000,
          gross_exposure_notional DOUBLE PRECISION NOT NULL DEFAULT 0,
          net_exposure_notional DOUBLE PRECISION NOT NULL DEFAULT 0,
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE IF NOT EXISTS portfolio_fill_log (
          fill_id UUID PRIMARY KEY,
          account_id TEXT NOT NULL,
          order_id UUID NOT NULL,
          venue TEXT NOT NULL,
          canonical_symbol TEXT NOT NULL,
          timeframe TEXT NOT NULL,
          side TEXT NOT NULL,
          filled_notional DOUBLE PRECISION NOT NULL,
          event_ts TIMESTAMPTZ NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_portfolio_fill_log_symbol_ts
          ON portfolio_fill_log (account_id, venue, canonical_symbol, created_at DESC);
        ",
    )
    .await
}

async fn ensure_account_row(
    conn: &Client,
    account_id: &str,
    default_equity: f64,
) -> Result<(), tokio_postgres::Error> {
    conn.execute(
        "
        INSERT INTO portfolio_account_state (account_id, equity)
        VALUES ($1, $2)
        ON CONFLICT (account_id) DO NOTHING
        ",
        &[&account_id, &default_equity],
    )
    .await?;
    Ok(())
}

async fn load_order_side(
    conn: &Client,
    order_id: Uuid,
) -> Result<Option<JournalOrder>, tokio_postgres::Error> {
    let row = conn
        .query_opt(
            "
            SELECT side
            FROM execution_order_journal
            WHERE order_id = $1::uuid
            ",
            &[&order_id],
        )
        .await?;

    Ok(row.map(|r| JournalOrder {
        side: r.get::<_, String>(0).to_ascii_lowercase(),
    }))
}

async fn apply_fill(
    conn: &Client,
    cfg: &PortfolioConfig,
    fill: &FillEvent,
    side: &str,
) -> Result<(f64, f64), tokio_postgres::Error> {
    let signed = if side == "sell" {
        -fill.filled_notional
    } else {
        fill.filled_notional
    };

    conn.execute(
        "
        INSERT INTO portfolio_position_state (
          account_id, venue, canonical_symbol, timeframe,
          net_position_notional, gross_exposure_notional,
          last_order_id, last_fill_notional, last_fill_side, last_fill_ts
        ) VALUES (
          $1,$2,$3,$4,$5,$6,$7::uuid,$8,$9,$10
        )
        ON CONFLICT (account_id, venue, canonical_symbol, timeframe)
        DO UPDATE SET
          net_position_notional = portfolio_position_state.net_position_notional + EXCLUDED.net_position_notional,
          gross_exposure_notional = GREATEST(0, ABS(portfolio_position_state.net_position_notional + EXCLUDED.net_position_notional)),
          last_order_id = EXCLUDED.last_order_id,
          last_fill_notional = EXCLUDED.last_fill_notional,
          last_fill_side = EXCLUDED.last_fill_side,
          last_fill_ts = EXCLUDED.last_fill_ts,
          updated_at = now()
        ",
        &[
            &cfg.account_id,
            &fill.venue,
            &fill.canonical_symbol,
            &fill.timeframe,
            &signed,
            &signed.abs(),
            &fill.order_id,
            &fill.filled_notional,
            &side,
            &fill.event_ts,
        ],
    )
    .await?;

    conn.execute(
        "
        INSERT INTO portfolio_fill_log (
          fill_id, account_id, order_id, venue, canonical_symbol,
          timeframe, side, filled_notional, event_ts
        ) VALUES ($1::uuid,$2,$3::uuid,$4,$5,$6,$7,$8,$9)
        ",
        &[
            &Uuid::new_v4(),
            &cfg.account_id,
            &fill.order_id,
            &fill.venue,
            &fill.canonical_symbol,
            &fill.timeframe,
            &side,
            &fill.filled_notional,
            &fill.event_ts,
        ],
    )
    .await?;

    let row = conn
        .query_one(
            "
            SELECT
              COALESCE(SUM(ABS(net_position_notional)), 0) AS gross_exposure,
              COALESCE(SUM(net_position_notional), 0) AS net_exposure
            FROM portfolio_position_state
            WHERE account_id = $1
            ",
            &[&cfg.account_id],
        )
        .await?;

    let gross_exposure = row.get::<_, f64>(0);
    let net_exposure = row.get::<_, f64>(1);

    conn.execute(
        "
        UPDATE portfolio_account_state
        SET
          gross_exposure_notional = $2,
          net_exposure_notional = $3,
          updated_at = now()
        WHERE account_id = $1
        ",
        &[&cfg.account_id, &gross_exposure, &net_exposure],
    )
    .await?;

    Ok((gross_exposure, net_exposure))
}

async fn publish_snapshot(
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

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let service_name = "portfolio_engine";

    let brokers = env_or("KAFKA_BROKERS", "kafka:9092");
    let input_fill_topic = env_or("PORTFOLIO_INPUT_FILL_TOPIC", "exec.fill_received.v1");
    let snapshot_topic = env_or("PORTFOLIO_SNAPSHOT_TOPIC", "portfolio.snapshot.v1");
    let group_id = env_or("PORTFOLIO_GROUP_ID", "nitra-portfolio-engine-v1");
    let db_dsn = env_or(
        "DATABASE_URL",
        "postgresql://trading:trading@timescaledb:5432/trading",
    );

    let cfg = PortfolioConfig {
        account_id: env_or("PORTFOLIO_ACCOUNT_ID", "paper"),
        default_equity: env_f64_or("PORTFOLIO_DEFAULT_EQUITY", 100000.0).max(1.0),
    };

    let (conn, connection) = tokio_postgres::connect(&db_dsn, NoTls).await?;
    tokio::spawn(async move {
        if let Err(e) = connection.await {
            eprintln!("postgres connection error: {e}");
        }
    });

    ensure_portfolio_tables(&conn).await?;
    ensure_account_row(&conn, &cfg.account_id, cfg.default_equity).await?;

    let consumer: StreamConsumer = ClientConfig::new()
        .set("bootstrap.servers", &brokers)
        .set("group.id", &group_id)
        .set("enable.auto.commit", "false")
        .set("auto.offset.reset", "earliest")
        .create()?;
    consumer.subscribe(&[&input_fill_topic])?;

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
        if let Some(fill) = parse_fill(&payload) {
            if let Some(order) = load_order_side(&conn, fill.order_id).await? {
                let side = if order.side == "sell" { "sell" } else { "buy" };
                let (gross_exposure, net_exposure) = apply_fill(&conn, &cfg, &fill, side).await?;

                let event_key = format!(
                    "{}:{}:{}",
                    fill.venue, fill.canonical_symbol, fill.timeframe
                );
                publish_snapshot(
                    &producer,
                    &snapshot_topic,
                    &event_key,
                    json!({
                        "account_id": cfg.account_id,
                        "venue": fill.venue,
                        "canonical_symbol": fill.canonical_symbol,
                        "timeframe": fill.timeframe,
                        "event_ts": fill.event_ts.to_rfc3339(),
                        "position": {
                            "last_order_id": fill.order_id.to_string(),
                            "last_fill_notional": fill.filled_notional,
                            "last_fill_side": side,
                        },
                        "portfolio": {
                            "gross_exposure_notional": gross_exposure,
                            "net_exposure_notional": net_exposure,
                        }
                    }),
                )
                .await?;
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
    fn parse_fill_payload() {
        let payload = json!({
            "order_id": Uuid::nil().to_string(),
            "venue": "coinbase",
            "canonical_symbol": "BTCUSD",
            "filled_notional": 500.0,
            "event_ts": "2026-04-28T00:00:00Z"
        });
        let parsed = parse_fill(&payload).expect("fill");
        assert_eq!(parsed.venue, "coinbase");
        assert_eq!(parsed.canonical_symbol, "BTCUSD");
        assert_eq!(parsed.filled_notional, 500.0);
    }
}
