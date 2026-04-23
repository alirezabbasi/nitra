use chrono::Utc;
use rand::Rng;
use rdkafka::producer::{FutureProducer, FutureRecord};
use rdkafka::ClientConfig;
use serde_json::{json, Value};
use std::collections::HashMap;
use std::env;
use std::time::Duration;
use tokio::time::sleep;
use uuid::Uuid;

fn env_or(name: &str, default: &str) -> String {
    env::var(name).unwrap_or_else(|_| default.to_string())
}

fn csv_env(name: &str, default: &str) -> Vec<String> {
    env_or(name, default)
        .split(',')
        .map(|item| item.trim().to_string())
        .filter(|item| !item.is_empty())
        .collect()
}

fn compact_symbol(symbol: &str) -> String {
    symbol
        .trim()
        .to_uppercase()
        .chars()
        .filter(|ch| ch.is_ascii_alphanumeric())
        .collect()
}

fn compact_capital_symbol(symbol: &str) -> String {
    let upper = symbol.trim().to_uppercase();
    let prefix = "CS.D.";
    let suffix = ".MINI.IP";
    if upper.starts_with(prefix) && upper.ends_with(suffix) {
        let core = &upper[prefix.len()..upper.len() - suffix.len()];
        if core.len() == 6 && core.chars().all(|ch| ch.is_ascii_alphabetic()) {
            return core.to_string();
        }
    }
    compact_symbol(&upper)
}

fn compact_symbol_for_venue(venue: &str, symbol: &str) -> String {
    if venue.eq_ignore_ascii_case("capital") {
        return compact_capital_symbol(symbol);
    }
    compact_symbol(symbol)
}

fn infer_asset_class(symbol: &str) -> &'static str {
    let upper = symbol.to_uppercase();
    if upper.len() >= 6 {
        if let Some(base) = upper.strip_suffix("USD") {
            if matches!(
                base,
                "BTC"
                    | "ETH"
                    | "SOL"
                    | "ADA"
                    | "XRP"
                    | "LTC"
                    | "DOGE"
                    | "BNB"
                    | "AVAX"
                    | "DOT"
                    | "LINK"
            ) {
                return "crypto";
            }
        }
        if let Some(base) = upper.strip_suffix("USDT") {
            if matches!(
                base,
                "BTC"
                    | "ETH"
                    | "SOL"
                    | "ADA"
                    | "XRP"
                    | "LTC"
                    | "DOGE"
                    | "BNB"
                    | "AVAX"
                    | "DOT"
                    | "LINK"
            ) {
                return "crypto";
            }
        }
        if let Some(base) = upper.strip_suffix("USDC") {
            if matches!(
                base,
                "BTC"
                    | "ETH"
                    | "SOL"
                    | "ADA"
                    | "XRP"
                    | "LTC"
                    | "DOGE"
                    | "BNB"
                    | "AVAX"
                    | "DOT"
                    | "LINK"
            ) {
                return "crypto";
            }
        }
    }

    "fx"
}

fn price_precision(symbol: &str) -> u32 {
    let upper = symbol.to_uppercase();
    if infer_asset_class(&upper) == "crypto" {
        return 2;
    }
    if upper.ends_with("JPY") {
        return 3;
    }
    5
}

fn initial_price(symbol: &str) -> f64 {
    match symbol.to_uppercase().as_str() {
        "EURUSD" => 1.0850,
        "GBPUSD" => 1.2700,
        "USDJPY" => 156.20,
        "BTCUSD" => 67000.0,
        "ETHUSD" => 3200.0,
        "SOLUSD" => 150.0,
        "ADAUSD" => 0.46,
        "XRPUSD" => 0.54,
        _ => {
            let upper = symbol.to_uppercase();
            if infer_asset_class(&upper) == "crypto" {
                100.0
            } else if upper.ends_with("JPY") {
                150.0
            } else {
                1.0
            }
        }
    }
}

fn spread_amount(symbol: &str, mid_price: f64) -> f64 {
    if infer_asset_class(symbol) == "crypto" {
        return (mid_price * 0.0005).max(0.10);
    }
    if symbol.to_uppercase().ends_with("JPY") {
        return 0.01;
    }
    0.0001
}

fn step_amount(symbol: &str, mid_price: f64) -> f64 {
    if infer_asset_class(symbol) == "crypto" {
        return (mid_price * 0.0015).max(0.5);
    }
    if symbol.to_uppercase().ends_with("JPY") {
        return 0.08;
    }
    (mid_price * 0.0002).max(0.00005)
}

fn round_to_precision(value: f64, precision: u32) -> f64 {
    let factor = 10f64.powi(precision as i32);
    (value * factor).round() / factor
}

fn iso_now_utc() -> String {
    Utc::now().to_rfc3339()
}

fn build_envelope(payload: Value) -> Value {
    json!({
        "message_id": Uuid::new_v4().to_string(),
        "emitted_at": iso_now_utc(),
        "schema_version": 1,
        "headers": {},
        "payload": payload,
        "retry": Value::Null,
    })
}

async fn send_json(
    producer: &FutureProducer,
    topic: &str,
    key: &str,
    value: &Value,
) -> Result<(), Box<dyn std::error::Error>> {
    let payload = value.to_string();
    producer
        .send(
            FutureRecord::to(topic).key(key).payload(&payload),
            Duration::from_secs(5),
        )
        .await
        .map_err(|(e, _)| e)?;
    Ok(())
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let brokers = env_or("KAFKA_BROKERS", "kafka:9092");
    let raw_topic = env_or("INGESTION_RAW_TOPIC", "raw.market.oanda");
    let health_topic = env_or("INGESTION_HEALTH_TOPIC", "connector.health");
    let venue = env_or("INGESTION_VENUE", "oanda");
    let default_symbol = env_or("INGESTION_SYMBOL", "EURUSD");
    let mut source_symbols = csv_env("INGESTION_ENABLED_INSTRUMENTS", &default_symbol);
    if source_symbols.is_empty() {
        source_symbols.push(default_symbol.clone());
    }
    let output_symbols: Vec<String> = source_symbols
        .iter()
        .map(|symbol| compact_symbol_for_venue(&venue, symbol))
        .collect();
    let interval_secs = env_or("INGESTION_INTERVAL_SECS", "1.0")
        .parse::<f64>()
        .unwrap_or(1.0)
        .max(0.1);
    let connector_mode = env_or("CONNECTOR_MODE", "mock");

    let producer: FutureProducer = ClientConfig::new()
        .set("bootstrap.servers", &brokers)
        .set("message.timeout.ms", "5000")
        .create()?;

    let mut prices: HashMap<String, f64> = output_symbols
        .iter()
        .map(|symbol| (symbol.clone(), initial_price(symbol)))
        .collect();

    loop {
        for (source_symbol, output_symbol) in source_symbols.iter().zip(output_symbols.iter()) {
            let current_mid = *prices
                .get(output_symbol)
                .unwrap_or(&initial_price(output_symbol));
            let step = step_amount(output_symbol, current_mid);
            let mut rng = rand::thread_rng();
            let next_mid = (current_mid + rng.gen_range(-step..=step)).max(0.00001);
            prices.insert(output_symbol.clone(), next_mid);

            let spread = spread_amount(output_symbol, next_mid);
            let precision = price_precision(output_symbol);
            let bid = round_to_precision((next_mid - (spread / 2.0)).max(0.00001), precision);
            let ask = round_to_precision((next_mid + (spread / 2.0)).max(bid), precision);
            let mid = round_to_precision((bid + ask) / 2.0, precision);

            let raw_payload = json!({
                "venue": venue,
                "broker_symbol": output_symbol,
                "event_ts_received": iso_now_utc(),
                "payload": {
                    "bid": bid,
                    "ask": ask,
                    "mid": mid,
                    "sequence_id": Uuid::new_v4().to_string(),
                    "source_symbol": source_symbol,
                },
                "source": "nitra.market_ingestion.mock",
            });

            let health_payload = json!({
                "service": "market-ingestion",
                "status": "ok",
                "mode": connector_mode,
                "venue": venue,
                "symbol": output_symbol,
                "source_symbol": source_symbol,
                "enabled_instruments": output_symbols,
                "ts": iso_now_utc(),
            });

            send_json(
                &producer,
                &raw_topic,
                output_symbol,
                &build_envelope(raw_payload),
            )
            .await?;

            send_json(
                &producer,
                &health_topic,
                output_symbol,
                &build_envelope(health_payload),
            )
            .await?;
        }

        sleep(Duration::from_secs_f64(interval_secs)).await;
    }
}
