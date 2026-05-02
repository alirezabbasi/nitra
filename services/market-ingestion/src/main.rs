use chrono::{Datelike, Timelike, Utc};
use rdkafka::producer::{FutureProducer, FutureRecord};
use rdkafka::ClientConfig;
use reqwest::header::{HeaderMap, HeaderName, HeaderValue, ACCEPT, CONTENT_TYPE};
use reqwest::{Client, StatusCode};
use serde_json::{json, Value};
use std::collections::{HashMap, HashSet};
use std::env;
use std::time::Duration;
use tokio::time::sleep;
use tokio_postgres::NoTls;
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

#[derive(Clone, Debug)]
struct FeedSlaState {
    last_success_at: Option<chrono::DateTime<Utc>>,
    max_fetch_latency_ms: i64,
    total_fetches: u64,
    fetch_errors: u64,
    dropped_quotes: u64,
    sequence_discontinuities: u64,
    last_seq_by_symbol: HashMap<String, i64>,
}

impl FeedSlaState {
    fn new() -> Self {
        Self {
            last_success_at: None,
            max_fetch_latency_ms: 0,
            total_fetches: 0,
            fetch_errors: 0,
            dropped_quotes: 0,
            sequence_discontinuities: 0,
            last_seq_by_symbol: HashMap::new(),
        }
    }
}

#[derive(Clone, Debug)]
struct RateLimitPolicy {
    enabled: bool,
    min_poll_interval_ms: u64,
    max_poll_interval_ms: u64,
    backoff_multiplier: f64,
    recovery_step_ms: u64,
    burst_cooldown_seconds: u64,
    max_consecutive_rate_limit_hits: u32,
    per_minute_soft_limit: i32,
}

impl RateLimitPolicy {
    fn from_env(base_interval_secs: f64) -> Self {
        let base_ms = (base_interval_secs * 1000.0).max(100.0) as u64;
        let min_ms = env_or("INGESTION_RATE_LIMIT_MIN_POLL_MS", &base_ms.to_string())
            .parse::<u64>()
            .unwrap_or(base_ms)
            .max(100);
        let max_ms = env_or("INGESTION_RATE_LIMIT_MAX_POLL_MS", "8000")
            .parse::<u64>()
            .unwrap_or(8000)
            .max(min_ms);
        let backoff_multiplier = env_or("INGESTION_RATE_LIMIT_BACKOFF_MULTIPLIER", "1.6")
            .parse::<f64>()
            .unwrap_or(1.6)
            .clamp(1.0, 5.0);
        let recovery_step_ms = env_or("INGESTION_RATE_LIMIT_RECOVERY_STEP_MS", "100")
            .parse::<u64>()
            .unwrap_or(100)
            .max(10);
        let burst_cooldown_seconds = env_or("INGESTION_RATE_LIMIT_BURST_COOLDOWN_SECONDS", "30")
            .parse::<u64>()
            .unwrap_or(30)
            .max(1);
        let max_consecutive_rate_limit_hits =
            env_or("INGESTION_RATE_LIMIT_MAX_CONSECUTIVE_HITS", "3")
                .parse::<u32>()
                .unwrap_or(3)
                .max(1);
        let per_minute_soft_limit = env_or("INGESTION_RATE_LIMIT_SOFT_LIMIT_PER_MINUTE", "120")
            .parse::<i32>()
            .unwrap_or(120)
            .max(1);
        let enabled = env_or("INGESTION_RATE_LIMIT_POLICY_ENABLED", "true")
            .eq_ignore_ascii_case("true");

        Self {
            enabled,
            min_poll_interval_ms: min_ms,
            max_poll_interval_ms: max_ms,
            backoff_multiplier,
            recovery_step_ms,
            burst_cooldown_seconds,
            max_consecutive_rate_limit_hits,
            per_minute_soft_limit,
        }
    }
}

#[derive(Clone, Debug)]
struct RateLimitState {
    effective_poll_interval_ms: u64,
    rate_limit_hits: u64,
    consecutive_rate_limit_hits: u32,
    last_rate_limited_at: Option<chrono::DateTime<Utc>>,
    cooldown_until: Option<chrono::DateTime<Utc>>,
    policy_last_loaded_at: Option<chrono::DateTime<Utc>>,
}

impl RateLimitState {
    fn new(initial_poll_interval_ms: u64) -> Self {
        Self {
            effective_poll_interval_ms: initial_poll_interval_ms,
            rate_limit_hits: 0,
            consecutive_rate_limit_hits: 0,
            last_rate_limited_at: None,
            cooldown_until: None,
            policy_last_loaded_at: None,
        }
    }
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

fn int_env(name: &str, default: i32) -> i32 {
    env::var(name)
        .ok()
        .and_then(|raw| raw.parse::<i32>().ok())
        .unwrap_or(default)
}

fn parse_sequence_number(sequence_id: &str) -> Option<i64> {
    let mut digits = String::new();
    for ch in sequence_id.chars().rev() {
        if ch.is_ascii_digit() {
            digits.push(ch);
            if digits.len() >= 18 {
                break;
            }
        } else if !digits.is_empty() {
            break;
        }
    }
    if digits.is_empty() {
        return None;
    }
    let rev: String = digits.chars().rev().collect();
    rev.parse::<i64>().ok()
}

fn looks_rate_limited(message: &str) -> bool {
    let lower = message.to_ascii_lowercase();
    lower.contains("429")
        || lower.contains("too many requests")
        || lower.contains("rate limit")
        || lower.contains("throttl")
}

fn is_crypto_symbol(symbol: &str) -> bool {
    let upper = compact_symbol(symbol);
    let crypto_bases = [
        "BTC", "ETH", "SOL", "ADA", "XRP", "LTC", "DOGE", "BNB", "AVAX", "DOT", "LINK",
    ];
    if upper.len() >= 6 && upper.ends_with("USD") {
        let base = &upper[..upper.len() - 3];
        return crypto_bases.contains(&base);
    }
    if upper.len() >= 7 && upper.ends_with("USDT") {
        let base = &upper[..upper.len() - 4];
        return crypto_bases.contains(&base);
    }
    if upper.len() >= 7 && upper.ends_with("USDC") {
        let base = &upper[..upper.len() - 4];
        return crypto_bases.contains(&base);
    }
    false
}

fn minute_of_week(now: &chrono::DateTime<Utc>) -> i32 {
    (now.weekday().number_from_monday() as i32 - 1) * 24 * 60
        + (now.hour() as i32 * 60)
        + now.minute() as i32
}

fn fx_market_weekend_closed(now: &chrono::DateTime<Utc>) -> bool {
    let start_dow = int_env("FX_WEEKEND_START_ISO_DOW", 6).clamp(1, 7);
    let start_hour = int_env("FX_WEEKEND_START_HOUR_UTC", 0).clamp(0, 23);
    let end_dow = int_env("FX_WEEKEND_END_ISO_DOW", 1).clamp(1, 7);
    let end_hour = int_env("FX_WEEKEND_END_HOUR_UTC", 6).clamp(0, 23);

    let start_minute = ((start_dow - 1) * 24 + start_hour) * 60;
    let end_minute = ((end_dow - 1) * 24 + end_hour) * 60;
    let now_minute = minute_of_week(now);

    if start_minute < end_minute {
        now_minute >= start_minute && now_minute < end_minute
    } else {
        now_minute >= start_minute || now_minute < end_minute
    }
}

fn is_fx_venue(venue: &str) -> bool {
    matches!(venue, "oanda" | "capital")
}

async fn load_symbols_from_db(
    database_url: &str,
    venue: &str,
) -> Result<Vec<String>, Box<dyn std::error::Error>> {
    let (client, connection) = tokio_postgres::connect(database_url, NoTls).await?;
    tokio::spawn(async move {
        if let Err(err) = connection.await {
            eprintln!("market-ingestion postgres connection error: {}", err);
        }
    });

    let rows = client
        .query(
            "SELECT symbol FROM venue_market WHERE venue = $1 AND enabled = TRUE AND ingest_enabled = TRUE ORDER BY symbol",
            &[&venue],
        )
        .await?;

    let mut symbols = Vec::new();
    for row in rows {
        let raw_symbol: String = row.get(0);
        let normalized = compact_symbol_for_venue(venue, &raw_symbol);
        if normalized.is_empty() {
            continue;
        }
        if !symbols.contains(&normalized) {
            symbols.push(normalized);
        }
    }
    Ok(symbols)
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
    feed_sla_state: &FeedSlaState,
    last_fetch_latency_ms: i64,
    rate_policy: &RateLimitPolicy,
    rate_state: &RateLimitState,
) -> Result<(), Box<dyn std::error::Error>> {
    let now = Utc::now();
    let heartbeat_age_seconds = feed_sla_state
        .last_success_at
        .map(|last| (now - last).num_seconds().max(0))
        .unwrap_or(-1);
    let last_rate_limited_at = rate_state
        .last_rate_limited_at
        .map(|v| v.to_rfc3339());
    let cooldown_until = rate_state.cooldown_until.map(|v| v.to_rfc3339());
    let policy_loaded_at = rate_state
        .policy_last_loaded_at
        .map(|v| v.to_rfc3339());
    let health_payload = json!({
        "service": "market-ingestion",
        "status": status,
        "mode": mode,
        "venue": venue,
        "enabled_instruments": symbols,
        "emitted_count": emitted_count,
        "last_error": last_error,
        "feed_quality": {
            "latency_ms": last_fetch_latency_ms,
            "max_latency_ms": feed_sla_state.max_fetch_latency_ms,
            "drop_count": feed_sla_state.dropped_quotes,
            "sequence_discontinuity_count": feed_sla_state.sequence_discontinuities,
            "heartbeat_age_seconds": heartbeat_age_seconds,
            "fetch_errors": feed_sla_state.fetch_errors,
            "fetch_count": feed_sla_state.total_fetches
        },
        "rate_limit": {
            "enabled": rate_policy.enabled,
            "effective_poll_interval_ms": rate_state.effective_poll_interval_ms,
            "rate_limit_hits": rate_state.rate_limit_hits,
            "consecutive_rate_limit_hits": rate_state.consecutive_rate_limit_hits,
            "cooldown_until": cooldown_until,
            "last_rate_limited_at": last_rate_limited_at,
            "policy_loaded_at": policy_loaded_at,
            "policy": {
                "min_poll_interval_ms": rate_policy.min_poll_interval_ms,
                "max_poll_interval_ms": rate_policy.max_poll_interval_ms,
                "backoff_multiplier": rate_policy.backoff_multiplier,
                "recovery_step_ms": rate_policy.recovery_step_ms,
                "burst_cooldown_seconds": rate_policy.burst_cooldown_seconds,
                "max_consecutive_rate_limit_hits": rate_policy.max_consecutive_rate_limit_hits,
                "per_minute_soft_limit": rate_policy.per_minute_soft_limit
            }
        },
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

async fn load_rate_limit_policy_from_db(
    database_url: &str,
    venue: &str,
    fallback: &RateLimitPolicy,
) -> Option<RateLimitPolicy> {
    if database_url.trim().is_empty() {
        return None;
    }
    let connect_result = tokio_postgres::connect(database_url, NoTls).await;
    let Ok((client, connection)) = connect_result else {
        return None;
    };
    tokio::spawn(async move {
        let _ = connection.await;
    });
    let row = client
        .query_opt(
            "SELECT enabled, min_poll_interval_ms, max_poll_interval_ms, backoff_multiplier, recovery_step_ms, burst_cooldown_seconds, max_consecutive_rate_limit_hits, per_minute_soft_limit FROM control_panel_ingestion_rate_limit_policy WHERE venue = $1",
            &[&venue],
        )
        .await
        .ok()
        .flatten()?;
    let enabled: bool = row.get(0);
    let min_poll_interval_ms: i32 = row.get(1);
    let max_poll_interval_ms: i32 = row.get(2);
    let backoff_multiplier: f64 = row.get(3);
    let recovery_step_ms: i32 = row.get(4);
    let burst_cooldown_seconds: i32 = row.get(5);
    let max_consecutive_rate_limit_hits: i32 = row.get(6);
    let per_minute_soft_limit: i32 = row.get(7);

    Some(RateLimitPolicy {
        enabled,
        min_poll_interval_ms: (min_poll_interval_ms as u64).max(100),
        max_poll_interval_ms: (max_poll_interval_ms as u64).max((min_poll_interval_ms as u64).max(100)),
        backoff_multiplier: backoff_multiplier.clamp(1.0, 5.0),
        recovery_step_ms: (recovery_step_ms as u64).max(10),
        burst_cooldown_seconds: (burst_cooldown_seconds as u64).max(1),
        max_consecutive_rate_limit_hits: (max_consecutive_rate_limit_hits as u32).max(1),
        per_minute_soft_limit: per_minute_soft_limit.max(1),
    })
    .or_else(|| Some(fallback.clone()))
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
    let env_symbols: Vec<String> = source_symbols
        .iter()
        .map(|symbol| compact_symbol_for_venue(&venue, symbol))
        .collect();
    let mut configured_symbols = env_symbols.clone();
    let interval_secs = env_or("INGESTION_INTERVAL_SECS", "1.0")
        .parse::<f64>()
        .unwrap_or(1.0)
        .max(0.1);
    let database_url = env_or("DATABASE_URL", "");
    let symbol_source = env_or("INGESTION_SYMBOL_SOURCE", "database").to_ascii_lowercase();
    let db_refresh_secs = env_or("INGESTION_DB_REFRESH_SECS", "30")
        .parse::<u64>()
        .unwrap_or(30)
        .max(5);
    let mut last_db_refresh = std::time::Instant::now() - Duration::from_secs(db_refresh_secs);

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
    let mut feed_sla_state = FeedSlaState::new();
    let mut rate_policy = RateLimitPolicy::from_env(interval_secs);
    let mut rate_state = RateLimitState::new(rate_policy.min_poll_interval_ms);
    let policy_refresh_secs = env_or("INGESTION_RATE_LIMIT_POLICY_REFRESH_SECS", "30")
        .parse::<u64>()
        .unwrap_or(30)
        .max(5);
    let mut last_policy_refresh = std::time::Instant::now() - Duration::from_secs(policy_refresh_secs);
    let mut last_fetch_latency_ms: i64 = 0;

    loop {
        if last_policy_refresh.elapsed() >= Duration::from_secs(policy_refresh_secs) {
            if let Some(policy) =
                load_rate_limit_policy_from_db(&database_url, &venue, &rate_policy).await
            {
                rate_policy = policy;
                rate_state.policy_last_loaded_at = Some(Utc::now());
                if rate_state.effective_poll_interval_ms < rate_policy.min_poll_interval_ms {
                    rate_state.effective_poll_interval_ms = rate_policy.min_poll_interval_ms;
                }
                if rate_state.effective_poll_interval_ms > rate_policy.max_poll_interval_ms {
                    rate_state.effective_poll_interval_ms = rate_policy.max_poll_interval_ms;
                }
            }
            last_policy_refresh = std::time::Instant::now();
        }

        if let Some(cooldown_until) = rate_state.cooldown_until {
            if cooldown_until > Utc::now() {
                let wait_ms = (cooldown_until - Utc::now()).num_milliseconds().max(50) as u64;
                sleep(Duration::from_millis(wait_ms)).await;
            } else {
                rate_state.cooldown_until = None;
            }
        }

        if symbol_source != "env"
            && !database_url.trim().is_empty()
            && last_db_refresh.elapsed() >= Duration::from_secs(db_refresh_secs)
        {
            match load_symbols_from_db(&database_url, &venue).await {
                Ok(db_symbols) if !db_symbols.is_empty() => {
                    configured_symbols = db_symbols;
                }
                Ok(_) => {
                    configured_symbols = env_symbols.clone();
                }
                Err(err) => {
                    eprintln!(
                        "market-ingestion failed to refresh symbols from DB (venue={}): {}",
                        venue, err
                    );
                    configured_symbols = env_symbols.clone();
                }
            }
            last_db_refresh = std::time::Instant::now();
        }

        let now = Utc::now();
        let fx_closed = is_fx_venue(&venue) && fx_market_weekend_closed(&now);
        let active_symbols: Vec<String> = configured_symbols
            .iter()
            .filter(|symbol| !fx_closed || is_crypto_symbol(symbol))
            .cloned()
            .collect();
        let output_symbols: Vec<String> = active_symbols
            .iter()
            .map(|symbol| compact_symbol_for_venue(&venue, symbol))
            .collect();

        if active_symbols.is_empty() {
            let pause_reason = if fx_closed {
                "FX weekend market is closed (Saturday 00:00 UTC to Monday 06:00 UTC by default)"
            } else {
                "no enabled symbols configured"
            };
            emit_health(
                &producer,
                &health_topic,
                &venue,
                &configured_symbols,
                "paused",
                &connector_mode,
                0,
                Some(pause_reason),
                &feed_sla_state,
                last_fetch_latency_ms,
                &rate_policy,
                &rate_state,
            )
            .await?;
            let sleep_ms = if rate_policy.enabled {
                rate_state.effective_poll_interval_ms
            } else {
                (interval_secs * 1000.0) as u64
            };
            sleep(Duration::from_millis(sleep_ms.max(100))).await;
            continue;
        }

        let fetch_started = std::time::Instant::now();
        let fetch_result = match venue.as_str() {
            "coinbase" => fetch_coinbase_quotes(&client, &active_symbols).await,
            "oanda" => fetch_oanda_quotes(&client, &active_symbols).await,
            "capital" => fetch_capital_quotes(&client, &active_symbols, &mut capital_headers).await,
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
                feed_sla_state.total_fetches += 1;
                last_fetch_latency_ms = fetch_started.elapsed().as_millis() as i64;
                feed_sla_state.max_fetch_latency_ms =
                    feed_sla_state.max_fetch_latency_ms.max(last_fetch_latency_ms);
                feed_sla_state.last_success_at = Some(Utc::now());
                if quotes.len() < active_symbols.len() {
                    feed_sla_state.dropped_quotes += (active_symbols.len() - quotes.len()) as u64;
                }
                for quote in &quotes {
                    if let Some(seq) = parse_sequence_number(&quote.sequence_id) {
                        let key = format!("{}:{}", venue, quote.broker_symbol);
                        if let Some(prev) = feed_sla_state.last_seq_by_symbol.get(&key) {
                            if seq <= *prev {
                                feed_sla_state.sequence_discontinuities += 1;
                            } else if seq - *prev > 100 {
                                feed_sla_state.sequence_discontinuities += 1;
                            }
                        }
                        feed_sla_state.last_seq_by_symbol.insert(key, seq);
                    }
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
                if rate_policy.enabled {
                    rate_state.consecutive_rate_limit_hits = 0;
                    if rate_state.effective_poll_interval_ms > rate_policy.min_poll_interval_ms {
                        rate_state.effective_poll_interval_ms = rate_state
                            .effective_poll_interval_ms
                            .saturating_sub(rate_policy.recovery_step_ms)
                            .max(rate_policy.min_poll_interval_ms);
                    }
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
                    &feed_sla_state,
                    last_fetch_latency_ms,
                    &rate_policy,
                    &rate_state,
                )
                .await?;
            }
            Err(err) => {
                let msg = err.to_string();
                eprintln!("market-ingestion fetch error ({}): {}", venue, msg);
                feed_sla_state.total_fetches += 1;
                feed_sla_state.fetch_errors += 1;
                last_fetch_latency_ms = fetch_started.elapsed().as_millis() as i64;
                feed_sla_state.max_fetch_latency_ms =
                    feed_sla_state.max_fetch_latency_ms.max(last_fetch_latency_ms);
                if rate_policy.enabled {
                    rate_state.effective_poll_interval_ms = ((rate_state.effective_poll_interval_ms
                        as f64)
                        * rate_policy.backoff_multiplier)
                        .round() as u64;
                    if rate_state.effective_poll_interval_ms > rate_policy.max_poll_interval_ms {
                        rate_state.effective_poll_interval_ms = rate_policy.max_poll_interval_ms;
                    }
                    if looks_rate_limited(&msg) {
                        rate_state.rate_limit_hits += 1;
                        rate_state.consecutive_rate_limit_hits += 1;
                        rate_state.last_rate_limited_at = Some(Utc::now());
                        if rate_state.consecutive_rate_limit_hits
                            >= rate_policy.max_consecutive_rate_limit_hits
                        {
                            rate_state.cooldown_until = Some(
                                Utc::now()
                                    + chrono::Duration::seconds(
                                        rate_policy.burst_cooldown_seconds as i64,
                                    ),
                            );
                        }
                    } else {
                        rate_state.consecutive_rate_limit_hits = 0;
                    }
                }
                emit_health(
                    &producer,
                    &health_topic,
                    &venue,
                    &output_symbols,
                    "degraded",
                    &connector_mode,
                    0,
                    Some(&msg),
                    &feed_sla_state,
                    last_fetch_latency_ms,
                    &rate_policy,
                    &rate_state,
                )
                .await?;
            }
        }

        let sleep_ms = if rate_policy.enabled {
            rate_state.effective_poll_interval_ms
        } else {
            (interval_secs * 1000.0) as u64
        };
        sleep(Duration::from_millis(sleep_ms.max(100))).await;
    }
}
