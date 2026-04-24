use chrono::Utc;
use rdkafka::producer::{FutureProducer, FutureRecord};
use rdkafka::ClientConfig;
use reqwest::header::{HeaderMap, HeaderName, HeaderValue, ACCEPT, CONTENT_TYPE};
use reqwest::{Client, StatusCode};
use serde_json::{json, Value};
use std::collections::{HashMap, HashSet};
use std::env;
use std::time::Duration;
use tokio::time::sleep;
use uuid::Uuid;

#[derive(Clone, Debug)]
struct VenueQuote {
    broker_symbol: String,
    source_symbol: String,
    bid: f64,
    ask: f64,
    mid: f64,
    event_ts_exchange: String,
    sequence_id: String,
}

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

fn iso_now_utc() -> String {
    Utc::now().to_rfc3339()
}

fn parse_f64(value: Option<&Value>) -> Option<f64> {
    let value = value?;
    if let Some(v) = value.as_f64() {
        return Some(v);
    }
    value.as_str()?.parse::<f64>().ok()
}

fn oanda_instrument_map() -> HashMap<String, String> {
    let mut out = HashMap::new();
    let mapping_raw = env::var("OANDA_INSTRUMENT_MAP").unwrap_or_default();
    if mapping_raw.trim().is_empty() {
        return out;
    }

    if let Ok(parsed) = serde_json::from_str::<Value>(&mapping_raw) {
        if let Some(obj) = parsed.as_object() {
            for (key, value) in obj {
                if let Some(mapped) = value.as_str() {
                    let canonical = compact_symbol(key);
                    let venue_symbol = mapped.trim().to_uppercase();
                    if !canonical.is_empty() && !venue_symbol.is_empty() {
                        out.insert(canonical, venue_symbol);
                    }
                }
            }
        }
    }
    out
}

fn oanda_instrument(symbol: &str, mapping: &HashMap<String, String>) -> String {
    let compact = compact_symbol(symbol);
    if let Some(mapped) = mapping.get(&compact) {
        return mapped.clone();
    }

    let raw = symbol.trim().to_uppercase();
    if raw.contains('_') {
        return raw;
    }

    if compact.len() == 6 && compact.chars().all(|ch| ch.is_ascii_alphabetic()) {
        return format!("{}_{}", &compact[0..3], &compact[3..6]);
    }
    if compact.ends_with("USD") && compact.len() > 3 {
        return format!("{}_USD", &compact[..compact.len() - 3]);
    }
    compact
}

fn coinbase_product(symbol: &str) -> String {
    let compact = compact_symbol(symbol);
    if compact.len() == 6 && compact.chars().all(|ch| ch.is_ascii_alphabetic()) {
        return format!("{}-{}", &compact[0..3], &compact[3..6]);
    }
    if compact.ends_with("USD") && compact.len() > 3 {
        let base = &compact[..compact.len() - 3];
        if !base.is_empty() {
            return format!("{}-USD", base);
        }
    }
    compact
}

fn parse_capital_price(value: Option<&Value>) -> Option<f64> {
    let value = value?;
    if let Some(v) = value.as_f64() {
        return Some(v);
    }
    if let Some(v) = value.as_str().and_then(|raw| raw.parse::<f64>().ok()) {
        return Some(v);
    }

    let obj = value.as_object()?;
    let bid = parse_f64(obj.get("bid"));
    let ask = parse_f64(obj.get("ask"));
    match (bid, ask) {
        (Some(b), Some(a)) => Some((b + a) / 2.0),
        (Some(b), None) => Some(b),
        (None, Some(a)) => Some(a),
        _ => None,
    }
}

fn capital_base_url() -> String {
    env_or("CAPITAL_API_URL", "https://api-capital.backend-capital.com")
        .trim_end_matches('/')
        .to_string()
}

fn capital_epic_candidates(symbol: &str) -> Vec<String> {
    let mut candidates: Vec<String> = Vec::new();

    let mapping_raw = env::var("CAPITAL_EPIC_MAP").unwrap_or_default();
    if !mapping_raw.trim().is_empty() {
        if let Ok(parsed) = serde_json::from_str::<Value>(&mapping_raw) {
            if let Some(mapped) = parsed
                .as_object()
                .and_then(|obj| obj.get(&compact_symbol(symbol)))
                .and_then(|v| v.as_str())
            {
                candidates.push(mapped.trim().to_string());
            }
        }
    }

    let compact = compact_symbol(symbol);
    candidates.push(format!("CS.D.{}.MINI.IP", compact));
    candidates.push(compact.clone());

    let allowlist: HashSet<String> = csv_env("CAPITAL_EPIC_ALLOWLIST", "")
        .iter()
        .map(|v| v.to_uppercase())
        .collect();

    let mut out: Vec<String> = Vec::new();
    for candidate in candidates {
        if candidate.trim().is_empty() {
            continue;
        }
        if !allowlist.is_empty() {
            let up = candidate.to_uppercase();
            if !allowlist.contains(&up) && !allowlist.contains(&compact) {
                continue;
            }
        }
        if !out.contains(&candidate) {
            out.push(candidate);
        }
    }
    out
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

async fn fetch_coinbase_quotes(
    client: &Client,
    symbols: &[String],
) -> Result<Vec<VenueQuote>, Box<dyn std::error::Error>> {
    let base = env_or("COINBASE_REST_URL", "https://api.exchange.coinbase.com")
        .trim_end_matches('/')
        .to_string();
    let public_base = env_or("COINBASE_PUBLIC_REST_URL", "https://api.coinbase.com")
        .trim_end_matches('/')
        .to_string();

    let mut out = Vec::new();
    for symbol in symbols {
        let product = coinbase_product(symbol);
        let url = format!("{}/products/{}/ticker", base, product);
        let resp = client.get(&url).send().await?;
        let payload: Value = if resp.status().is_success() {
            resp.json().await?
        } else if matches!(
            resp.status(),
            StatusCode::BAD_REQUEST | StatusCode::NOT_FOUND | StatusCode::FORBIDDEN
        ) {
            let fallback_url = format!("{}/v2/prices/{}/spot", public_base, product);
            let fallback_resp = client.get(&fallback_url).send().await?;
            if !fallback_resp.status().is_success() {
                continue;
            }
            let fallback_payload: Value = fallback_resp.json().await?;
            let Some(amount) = fallback_payload
                .get("data")
                .and_then(|v| v.get("amount"))
                .and_then(|v| parse_f64(Some(v)))
            else {
                continue;
            };
            json!({
                "bid": amount,
                "ask": amount,
                "price": amount,
                "time": iso_now_utc(),
                "trade_id": Uuid::new_v4().to_string(),
            })
        } else {
            resp.error_for_status()?;
            continue;
        };

        let mut bid = parse_f64(payload.get("bid"));
        let mut ask = parse_f64(payload.get("ask"));
        let price = parse_f64(payload.get("price"));

        if bid.is_none() && ask.is_none() {
            bid = price;
            ask = price;
        } else if bid.is_none() {
            bid = ask;
        } else if ask.is_none() {
            ask = bid;
        }

        let (bid, ask) = match (bid, ask) {
            (Some(b), Some(a)) => (b, a),
            _ => continue,
        };

        let ts = payload
            .get("time")
            .and_then(|v| v.as_str())
            .map(|v| v.to_string())
            .unwrap_or_else(iso_now_utc);

        let sequence_id = payload
            .get("trade_id")
            .and_then(|v| v.as_i64())
            .map(|v| v.to_string())
            .unwrap_or_else(|| Uuid::new_v4().to_string());

        out.push(VenueQuote {
            broker_symbol: compact_symbol_for_venue("coinbase", symbol),
            source_symbol: product,
            bid,
            ask,
            mid: (bid + ask) / 2.0,
            event_ts_exchange: ts,
            sequence_id,
        });
    }

    Ok(out)
}

async fn fetch_oanda_quotes(
    client: &Client,
    symbols: &[String],
) -> Result<Vec<VenueQuote>, Box<dyn std::error::Error>> {
    let stream_url = env_or("OANDA_STREAM_URL", "https://stream-fxpractice.oanda.com");
    let rest_url_override = env_or("OANDA_REST_URL", "");
    let account_id = env_or("OANDA_ACCOUNT_ID", "");
    let api_token = env_or("OANDA_API_TOKEN", "");

    if account_id.trim().is_empty() || api_token.trim().is_empty() {
        return Err(std::io::Error::other(
            "oanda credentials missing: OANDA_ACCOUNT_ID/OANDA_API_TOKEN",
        )
        .into());
    }

    let api_base = if rest_url_override.trim().is_empty() {
        stream_url
            .replace("stream-fxpractice", "api-fxpractice")
            .replace("stream-fxtrade", "api-fxtrade")
            .split("/v3/")
            .next()
            .unwrap_or("https://api-fxpractice.oanda.com")
            .trim_end_matches('/')
            .to_string()
    } else {
        rest_url_override.trim_end_matches('/').to_string()
    };

    let oanda_mapping = oanda_instrument_map();
    let mut instrument_to_canonical: HashMap<String, String> = HashMap::new();
    let instruments: Vec<String> = symbols
        .iter()
        .map(|v| {
            let canonical = compact_symbol(v);
            let instrument = oanda_instrument(v, &oanda_mapping);
            instrument_to_canonical.insert(compact_symbol(&instrument), canonical);
            instrument
        })
        .collect();
    let url = format!(
        "{}/v3/accounts/{}/pricing?instruments={}",
        api_base,
        account_id,
        instruments.join(",")
    );

    let resp = client
        .get(&url)
        .header("Authorization", format!("Bearer {}", api_token))
        .header("Accept-Datetime-Format", "RFC3339")
        .send()
        .await?;
    let resp = resp.error_for_status()?;
    let payload: Value = resp.json().await?;

    let mut out = Vec::new();
    let enabled: HashSet<String> = symbols.iter().map(|v| compact_symbol(v)).collect();
    let Some(prices) = payload.get("prices").and_then(|v| v.as_array()) else {
        return Ok(out);
    };

    for row in prices {
        let instrument = row
            .get("instrument")
            .and_then(|v| v.as_str())
            .unwrap_or_default();
        let instrument_compact = compact_symbol(instrument);
        let broker_symbol = instrument_to_canonical
            .get(&instrument_compact)
            .cloned()
            .unwrap_or(instrument_compact);
        if !enabled.contains(&broker_symbol) {
            continue;
        }

        let bid = row
            .get("bids")
            .and_then(|v| v.as_array())
            .and_then(|arr| arr.first())
            .and_then(|entry| parse_f64(entry.get("price")));
        let ask = row
            .get("asks")
            .and_then(|v| v.as_array())
            .and_then(|arr| arr.first())
            .and_then(|entry| parse_f64(entry.get("price")));

        let (bid, ask) = match (bid, ask) {
            (Some(b), Some(a)) => (b, a),
            _ => continue,
        };

        let ts = row
            .get("time")
            .and_then(|v| v.as_str())
            .map(|v| v.to_string())
            .unwrap_or_else(iso_now_utc);

        out.push(VenueQuote {
            broker_symbol,
            source_symbol: instrument.to_string(),
            bid,
            ask,
            mid: (bid + ask) / 2.0,
            event_ts_exchange: ts.clone(),
            sequence_id: format!("{}:{}", instrument, ts),
        });
    }

    Ok(out)
}

async fn capital_auth_headers(client: &Client) -> Result<HeaderMap, Box<dyn std::error::Error>> {
    let api_key = env_or("CAPITAL_API_KEY", "");
    let identifier = env_or("CAPITAL_IDENTIFIER", "");
    let password = env_or("CAPITAL_API_PASSWORD", "");
    if api_key.trim().is_empty() || identifier.trim().is_empty() || password.trim().is_empty() {
        return Err(std::io::Error::other(
            "capital credentials missing: CAPITAL_API_KEY/CAPITAL_IDENTIFIER/CAPITAL_API_PASSWORD",
        )
        .into());
    }

    let url = format!("{}/api/v1/session", capital_base_url());
    let resp = client
        .post(url)
        .header("X-CAP-API-KEY", api_key.clone())
        .header(CONTENT_TYPE, "application/json")
        .header(ACCEPT, "application/json")
        .json(&json!({
            "identifier": identifier,
            "password": password,
            "encryptedPassword": false,
        }))
        .send()
        .await?;
    let resp = resp.error_for_status()?;

    let cst = resp
        .headers()
        .get("CST")
        .and_then(|v| v.to_str().ok())
        .ok_or_else(|| std::io::Error::other("capital CST header missing"))?
        .to_string();
    let security = resp
        .headers()
        .get("X-SECURITY-TOKEN")
        .and_then(|v| v.to_str().ok())
        .ok_or_else(|| std::io::Error::other("capital X-SECURITY-TOKEN header missing"))?
        .to_string();

    let mut headers = HeaderMap::new();
    headers.insert(ACCEPT, HeaderValue::from_static("application/json"));
    headers.insert(CONTENT_TYPE, HeaderValue::from_static("application/json"));
    headers.insert(
        HeaderName::from_static("x-cap-api-key"),
        HeaderValue::from_str(&api_key)?,
    );
    headers.insert(HeaderName::from_static("cst"), HeaderValue::from_str(&cst)?);
    headers.insert(
        HeaderName::from_static("x-security-token"),
        HeaderValue::from_str(&security)?,
    );
    Ok(headers)
}

async fn fetch_capital_quote_for_epic(
    client: &Client,
    headers: &HeaderMap,
    epic: &str,
) -> Result<Option<VenueQuote>, Box<dyn std::error::Error>> {
    let url = format!(
        "{}/api/v1/prices/{}?resolution=MINUTE&max=1",
        capital_base_url(),
        epic
    );

    let resp = client.get(url).headers(headers.clone()).send().await?;
    match resp.status() {
        StatusCode::NOT_FOUND => return Ok(None),
        StatusCode::UNAUTHORIZED | StatusCode::FORBIDDEN => {
            return Err(std::io::Error::other("capital auth expired").into());
        }
        s if !s.is_success() => {
            return Err(std::io::Error::other(format!(
                "capital price request failed: {} for epic {}",
                s, epic
            ))
            .into());
        }
        _ => {}
    }
    let payload: Value = resp.json().await?;

    let Some(first) = payload
        .get("prices")
        .and_then(|v| v.as_array())
        .and_then(|arr| arr.first())
    else {
        return Ok(None);
    };

    let close_price = first.get("closePrice");
    let bid = parse_f64(close_price.and_then(|v| v.get("bid")))
        .or_else(|| parse_capital_price(close_price));
    let ask = parse_f64(close_price.and_then(|v| v.get("ask")))
        .or_else(|| parse_capital_price(close_price));

    let (bid, ask) = match (bid, ask) {
        (Some(b), Some(a)) => (b, a),
        (Some(b), None) => (b, b),
        (None, Some(a)) => (a, a),
        _ => return Ok(None),
    };

    let ts = first
        .get("snapshotTimeUTC")
        .and_then(|v| v.as_str())
        .map(|v| format!("{}Z", v.trim_end_matches('Z')))
        .unwrap_or_else(iso_now_utc);

    Ok(Some(VenueQuote {
        broker_symbol: compact_capital_symbol(epic),
        source_symbol: epic.to_string(),
        bid,
        ask,
        mid: (bid + ask) / 2.0,
        event_ts_exchange: ts.clone(),
        sequence_id: format!("{}:{}", epic, ts),
    }))
}

fn is_capital_auth_error(err: &dyn std::error::Error) -> bool {
    err.to_string().contains("capital auth expired")
}

async fn fetch_capital_quotes(
    client: &Client,
    symbols: &[String],
    cached_headers: &mut Option<HeaderMap>,
) -> Result<Vec<VenueQuote>, Box<dyn std::error::Error>> {
    if cached_headers.is_none() {
        *cached_headers = Some(capital_auth_headers(client).await?);
    }

    let mut out = Vec::new();
    for symbol in symbols {
        let candidates = capital_epic_candidates(symbol);
        if candidates.is_empty() {
            continue;
        }

        let mut found_for_symbol = false;
        for epic in candidates {
            let headers = cached_headers
                .as_ref()
                .ok_or_else(|| std::io::Error::other("capital session headers unavailable"))?;
            let first_try = fetch_capital_quote_for_epic(client, headers, &epic).await;

            let quote = match first_try {
                Ok(v) => v,
                Err(err) if is_capital_auth_error(err.as_ref()) => {
                    *cached_headers = Some(capital_auth_headers(client).await?);
                    let refreshed = cached_headers
                        .as_ref()
                        .ok_or_else(|| std::io::Error::other("capital session headers unavailable"))?;
                    match fetch_capital_quote_for_epic(client, refreshed, &epic).await {
                        Ok(v) => v,
                        Err(retry_err) => {
                            eprintln!(
                                "market-ingestion capital quote error (epic={}): {}",
                                epic, retry_err
                            );
                            continue;
                        }
                    }
                }
                Err(err) => {
                    eprintln!(
                        "market-ingestion capital quote error (epic={}): {}",
                        epic, err
                    );
                    continue;
                }
            };

            if let Some(mut q) = quote {
                q.broker_symbol = compact_symbol_for_venue("capital", symbol);
                out.push(q);
                found_for_symbol = true;
                break;
            }
        }

        if !found_for_symbol {
            continue;
        }
    }

    Ok(out)
}

async fn emit_health(
    producer: &FutureProducer,
    topic: &str,
    venue: &str,
    symbols: &[String],
    status: &str,
    mode: &str,
    emitted_count: usize,
    last_error: Option<&str>,
) -> Result<(), Box<dyn std::error::Error>> {
    let health_payload = json!({
        "service": "market-ingestion",
        "status": status,
        "mode": mode,
        "venue": venue,
        "enabled_instruments": symbols,
        "emitted_count": emitted_count,
        "last_error": last_error,
        "ts": iso_now_utc(),
    });

    send_json(
        producer,
        topic,
        venue,
        &build_envelope(health_payload),
    )
    .await
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let brokers = env_or("KAFKA_BROKERS", "kafka:9092");
    let raw_topic = env_or("INGESTION_RAW_TOPIC", "raw.market.oanda");
    let health_topic = env_or("INGESTION_HEALTH_TOPIC", "connector.health");
    let venue = env_or("INGESTION_VENUE", "oanda").to_ascii_lowercase();
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

    let connector_mode = env_or("CONNECTOR_MODE", &venue).to_ascii_lowercase();
    if connector_mode == "mock" {
        return Err(std::io::Error::other(
            "CONNECTOR_MODE=mock is forbidden; ingestion must use venue-sourced data",
        )
        .into());
    }

    let producer: FutureProducer = ClientConfig::new()
        .set("bootstrap.servers", &brokers)
        .set("message.timeout.ms", "5000")
        .create()?;

    let client = Client::builder()
        .timeout(Duration::from_secs(15))
        .build()?;

    let mut capital_headers: Option<HeaderMap> = None;

    loop {
        let fetch_result = match venue.as_str() {
            "coinbase" => fetch_coinbase_quotes(&client, &source_symbols).await,
            "oanda" => fetch_oanda_quotes(&client, &source_symbols).await,
            "capital" => fetch_capital_quotes(&client, &source_symbols, &mut capital_headers).await,
            _ => {
                return Err(std::io::Error::other(format!(
                    "unsupported INGESTION_VENUE '{}' (expected oanda/capital/coinbase)",
                    venue
                ))
                .into());
            }
        };

        match fetch_result {
            Ok(quotes) => {
                for quote in &quotes {
                    let raw_payload = json!({
                        "venue": venue,
                        "broker_symbol": quote.broker_symbol,
                        "event_ts_received": iso_now_utc(),
                        "payload": {
                            "event_ts_exchange": quote.event_ts_exchange,
                            "bid": quote.bid,
                            "ask": quote.ask,
                            "mid": quote.mid,
                            "sequence_id": quote.sequence_id,
                            "source_symbol": quote.source_symbol,
                        },
                        "source": format!("nitra.market_ingestion.{}", venue),
                    });

                    send_json(
                        &producer,
                        &raw_topic,
                        &quote.broker_symbol,
                        &build_envelope(raw_payload),
                    )
                    .await?;
                }

                let status = if quotes.is_empty() { "degraded" } else { "ok" };
                let last_error = if quotes.is_empty() {
                    Some("venue request returned zero quotes")
                } else {
                    None
                };
                emit_health(
                    &producer,
                    &health_topic,
                    &venue,
                    &output_symbols,
                    status,
                    &connector_mode,
                    quotes.len(),
                    last_error,
                )
                .await?;
            }
            Err(err) => {
                let msg = err.to_string();
                eprintln!("market-ingestion fetch error ({}): {}", venue, msg);
                emit_health(
                    &producer,
                    &health_topic,
                    &venue,
                    &output_symbols,
                    "degraded",
                    &connector_mode,
                    0,
                    Some(&msg),
                )
                .await?;
            }
        }

        sleep(Duration::from_secs_f64(interval_secs)).await;
    }
}
