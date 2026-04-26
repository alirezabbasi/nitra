use chrono::{DateTime, Duration as ChronoDuration, Timelike, Utc};
use futures_util::StreamExt;
use rdkafka::consumer::{CommitMode, Consumer, StreamConsumer};
use rdkafka::message::BorrowedMessage;
use rdkafka::ClientConfig;
use rdkafka::Message;
use reqwest::header::{HeaderMap, HeaderValue};
use serde_json::Value;
use std::collections::{HashMap, HashSet};
use std::env;
use std::fs;
use std::time::Duration;
use tokio::task::JoinSet;
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

#[derive(Clone, Debug)]
struct HistoryFetchConfig {
    enabled: bool,
    timeout_secs: u64,
    oanda_rest_url: String,
    oanda_token: String,
    oanda_instrument_map: HashMap<String, String>,
    coinbase_rest_url: String,
    coinbase_public_rest_url: String,
    coinbase_user_agent: String,
    capital_api_url: String,
    capital_api_key: String,
    capital_identifier: String,
    capital_password: String,
    capital_epic_map: HashMap<String, String>,
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

fn parse_capital_epic_map(raw: &str) -> HashMap<String, String> {
    let mut out = HashMap::new();
    let Ok(value) = serde_json::from_str::<Value>(raw) else {
        return out;
    };
    let Some(map) = value.as_object() else {
        return out;
    };
    for (k, v) in map {
        if let Some(epic) = v.as_str() {
            let key = k.trim().to_ascii_uppercase();
            let val = epic.trim().to_string();
            if !key.is_empty() && !val.is_empty() {
                out.insert(key, val);
            }
        }
    }
    out
}

fn parse_symbol_map(raw: &str) -> HashMap<String, String> {
    let mut out = HashMap::new();
    let Ok(value) = serde_json::from_str::<Value>(raw) else {
        return out;
    };
    let Some(map) = value.as_object() else {
        return out;
    };
    for (k, v) in map {
        if let Some(symbol) = v.as_str() {
            let key = k.trim().to_ascii_uppercase();
            let val = symbol.trim().to_ascii_uppercase();
            if !key.is_empty() && !val.is_empty() {
                out.insert(key, val);
            }
        }
    }
    out
}

fn history_fetch_config() -> HistoryFetchConfig {
    let oanda_map_raw = env::var("REPLAY_OANDA_INSTRUMENT_MAP")
        .ok()
        .filter(|v| !v.trim().is_empty())
        .or_else(|| env::var("OANDA_INSTRUMENT_MAP").ok())
        .unwrap_or_default();
    let epic_map_raw = env::var("REPLAY_CAPITAL_EPIC_MAP")
        .ok()
        .filter(|v| !v.trim().is_empty())
        .or_else(|| env::var("CAPITAL_EPIC_MAP").ok())
        .unwrap_or_default();

    HistoryFetchConfig {
        enabled: env_bool_or("REPLAY_HISTORY_ENABLED", true),
        timeout_secs: env_u64_or("REPLAY_HISTORY_TIMEOUT_SECS", 8).max(3),
        oanda_rest_url: env_or(
            "REPLAY_OANDA_REST_URL",
            &env_or("OANDA_REST_URL", "https://api-fxpractice.oanda.com"),
        ),
        oanda_token: env_or("REPLAY_OANDA_API_TOKEN", &env_or("OANDA_API_TOKEN", "")),
        oanda_instrument_map: parse_symbol_map(&oanda_map_raw),
        coinbase_rest_url: env_or(
            "REPLAY_COINBASE_REST_URL",
            &env_or("COINBASE_REST_URL", "https://api.exchange.coinbase.com"),
        ),
        coinbase_public_rest_url: env_or(
            "REPLAY_COINBASE_PUBLIC_REST_URL",
            &env_or("COINBASE_PUBLIC_REST_URL", "https://api.coinbase.com"),
        ),
        coinbase_user_agent: env_or("REPLAY_COINBASE_USER_AGENT", "nitra-replay-controller/1.0"),
        capital_api_url: env_or(
            "REPLAY_CAPITAL_API_URL",
            &env_or("CAPITAL_API_URL", "https://api-capital.backend-capital.com"),
        ),
        capital_api_key: env_or("REPLAY_CAPITAL_API_KEY", &env_or("CAPITAL_API_KEY", "")),
        capital_identifier: env_or(
            "REPLAY_CAPITAL_IDENTIFIER",
            &env_or("CAPITAL_IDENTIFIER", ""),
        ),
        capital_password: env_or(
            "REPLAY_CAPITAL_API_PASSWORD",
            &env_or("CAPITAL_API_PASSWORD", ""),
        ),
        capital_epic_map: parse_capital_epic_map(&epic_map_raw),
    }
}

fn symbol_for_oanda(
    cfg: &HistoryFetchConfig,
    canonical: &str,
    broker_symbols: &[String],
) -> String {
    let canonical_upper = canonical.to_ascii_uppercase();
    if let Some(mapped) = cfg.oanda_instrument_map.get(&canonical_upper) {
        return mapped.clone();
    }

    if let Some(sym) = broker_symbols.iter().find(|s| s.contains('_')) {
        return sym.clone();
    }
    if canonical_upper.len() == 6 && canonical_upper.chars().all(|ch| ch.is_ascii_alphabetic()) {
        return format!("{}_{}", &canonical_upper[0..3], &canonical_upper[3..6]);
    }
    if canonical_upper.ends_with("USD") && canonical_upper.len() > 3 {
        return format!("{}_USD", &canonical_upper[..canonical_upper.len() - 3]);
    }
    if canonical_upper.chars().all(|ch| ch.is_ascii_alphanumeric())
        && canonical_upper.chars().any(|ch| ch.is_ascii_digit())
    {
        return format!("{}_USD", canonical_upper);
    }
    canonical_upper
}

fn symbol_for_coinbase(canonical: &str) -> String {
    if canonical.len() == 6 && canonical.chars().all(|ch| ch.is_ascii_alphabetic()) {
        return format!("{}-{}", &canonical[0..3], &canonical[3..6]);
    }
    canonical.to_string()
}

fn parse_capital_price(value: &Value) -> Option<f64> {
    if let Some(v) = value.as_f64() {
        return Some(v);
    }
    let Some(obj) = value.as_object() else {
        return None;
    };
    let bid = obj.get("bid").and_then(|v| v.as_f64());
    let ask = obj.get("ask").and_then(|v| v.as_f64());
    match (bid, ask) {
        (Some(b), Some(a)) => Some((b + a) / 2.0),
        (Some(b), None) => Some(b),
        (None, Some(a)) => Some(a),
        _ => None,
    }
}

fn parse_utc_minute(raw: &str) -> Option<DateTime<Utc>> {
    DateTime::parse_from_rfc3339(raw)
        .map(|v| minute_bucket(v.with_timezone(&Utc)))
        .ok()
}

async fn fetch_oanda_history_bars(
    client: &reqwest::Client,
    cfg: &HistoryFetchConfig,
    command: &ReplayCommand,
    broker_symbols: &[String],
) -> Result<Vec<BarRow>, String> {
    if cfg.oanda_token.trim().is_empty() {
        return Err("missing OANDA API token".to_string());
    }

    let instrument = symbol_for_oanda(cfg, &command.canonical_symbol, broker_symbols);
    let start = command.start_ts.to_rfc3339();
    let end = (command.end_ts + ChronoDuration::minutes(1)).to_rfc3339();
    let url = format!(
        "{}/v3/instruments/{}/candles",
        cfg.oanda_rest_url.trim_end_matches('/'),
        instrument
    );

    let response = client
        .get(url)
        .query(&[
            ("granularity", "M1"),
            ("price", "M"),
            ("from", start.as_str()),
            ("to", end.as_str()),
            ("includeFirst", "true"),
        ])
        .header("Authorization", format!("Bearer {}", cfg.oanda_token))
        .header("Accept-Datetime-Format", "RFC3339")
        .send()
        .await
        .map_err(|e| format!("oanda request error: {e}"))?;

    if !response.status().is_success() {
        let status = response.status();
        let body = response.text().await.unwrap_or_default();
        return Err(format!(
            "oanda HTTP {status}: {}",
            body.chars().take(240).collect::<String>()
        ));
    }

    let payload = response
        .json::<Value>()
        .await
        .map_err(|e| format!("oanda response parse error: {e}"))?;

    let Some(candles) = payload.get("candles").and_then(|v| v.as_array()) else {
        return Ok(Vec::new());
    };

    let mut out = Vec::new();
    for candle in candles {
        if !candle
            .get("complete")
            .and_then(|v| v.as_bool())
            .unwrap_or(false)
        {
            continue;
        }
        let ts = candle
            .get("time")
            .and_then(|v| v.as_str())
            .and_then(parse_utc_minute);
        let mid = candle.get("mid").and_then(|v| v.as_object());
        let open = mid
            .and_then(|m| m.get("o"))
            .and_then(|v| v.as_str())
            .and_then(|v| v.parse::<f64>().ok());
        let high = mid
            .and_then(|m| m.get("h"))
            .and_then(|v| v.as_str())
            .and_then(|v| v.parse::<f64>().ok());
        let low = mid
            .and_then(|m| m.get("l"))
            .and_then(|v| v.as_str())
            .and_then(|v| v.parse::<f64>().ok());
        let close = mid
            .and_then(|m| m.get("c"))
            .and_then(|v| v.as_str())
            .and_then(|v| v.parse::<f64>().ok());

        if let (Some(bucket_start), Some(open), Some(high), Some(low), Some(close)) =
            (ts, open, high, low, close)
        {
            out.push(BarRow {
                bucket_start,
                open,
                high,
                low,
                close,
                trade_count: 0,
                last_event_ts: bucket_start,
            });
        }
    }
    Ok(out)
}

async fn fetch_coinbase_history_bars(
    client: &reqwest::Client,
    cfg: &HistoryFetchConfig,
    command: &ReplayCommand,
) -> Result<Vec<BarRow>, String> {
    let product = symbol_for_coinbase(&command.canonical_symbol);
    let start = command.start_ts.to_rfc3339();
    let end = (command.end_ts + ChronoDuration::minutes(1)).to_rfc3339();

    let primary_url = format!(
        "{}/products/{}/candles",
        cfg.coinbase_rest_url.trim_end_matches('/'),
        product
    );
    let primary = client
        .get(primary_url)
        .query(&[
            ("granularity", "60"),
            ("start", start.as_str()),
            ("end", end.as_str()),
        ])
        .header("User-Agent", cfg.coinbase_user_agent.clone())
        .header("Accept", "application/json")
        .send()
        .await
        .map_err(|e| format!("coinbase exchange request error: {e}"))?;

    if primary.status().is_success() {
        let payload = primary
            .json::<Value>()
            .await
            .map_err(|e| format!("coinbase exchange parse error: {e}"))?;
        let mut out = Vec::new();
        if let Some(rows) = payload.as_array() {
            for row in rows {
                let Some(values) = row.as_array() else {
                    continue;
                };
                if values.len() < 5 {
                    continue;
                }
                let ts = values
                    .first()
                    .and_then(|v| v.as_i64())
                    .and_then(|secs| DateTime::from_timestamp(secs, 0))
                    .map(minute_bucket);
                let low = values.get(1).and_then(|v| v.as_f64());
                let high = values.get(2).and_then(|v| v.as_f64());
                let open = values.get(3).and_then(|v| v.as_f64());
                let close = values.get(4).and_then(|v| v.as_f64());
                if let (Some(bucket_start), Some(open), Some(high), Some(low), Some(close)) =
                    (ts, open, high, low, close)
                {
                    out.push(BarRow {
                        bucket_start,
                        open,
                        high,
                        low,
                        close,
                        trade_count: 0,
                        last_event_ts: bucket_start,
                    });
                }
            }
        }
        out.sort_by_key(|r| r.bucket_start);
        return Ok(out);
    }

    let status = primary.status().as_u16();
    if ![403, 429, 500, 503].contains(&status) {
        let body = primary.text().await.unwrap_or_default();
        return Err(format!(
            "coinbase exchange HTTP {}: {}",
            status,
            body.chars().take(240).collect::<String>()
        ));
    }

    let fallback_url = format!(
        "{}/api/v3/brokerage/market/products/{}/candles",
        cfg.coinbase_public_rest_url.trim_end_matches('/'),
        product
    );
    let fallback_start = command.start_ts.timestamp().to_string();
    let fallback_end = (command.end_ts + ChronoDuration::minutes(1))
        .timestamp()
        .to_string();
    let fallback = client
        .get(fallback_url)
        .query(&[
            ("granularity", "ONE_MINUTE"),
            ("start", fallback_start.as_str()),
            ("end", fallback_end.as_str()),
            ("limit", "350"),
        ])
        .header("User-Agent", cfg.coinbase_user_agent.clone())
        .header("Accept", "application/json")
        .send()
        .await
        .map_err(|e| format!("coinbase public fallback request error: {e}"))?;

    if !fallback.status().is_success() {
        let status = fallback.status();
        let body = fallback.text().await.unwrap_or_default();
        return Err(format!(
            "coinbase fallback HTTP {status}: {}",
            body.chars().take(240).collect::<String>()
        ));
    }

    let payload = fallback
        .json::<Value>()
        .await
        .map_err(|e| format!("coinbase fallback parse error: {e}"))?;
    let Some(candles) = payload.get("candles").and_then(|v| v.as_array()) else {
        return Ok(Vec::new());
    };

    let mut out = Vec::new();
    for candle in candles {
        let Some(obj) = candle.as_object() else {
            continue;
        };
        let ts = obj
            .get("start")
            .and_then(|v| v.as_str())
            .and_then(|v| v.parse::<i64>().ok())
            .and_then(|secs| DateTime::from_timestamp(secs, 0))
            .map(minute_bucket);
        let open = obj
            .get("open")
            .and_then(|v| v.as_str())
            .and_then(|v| v.parse::<f64>().ok());
        let high = obj
            .get("high")
            .and_then(|v| v.as_str())
            .and_then(|v| v.parse::<f64>().ok());
        let low = obj
            .get("low")
            .and_then(|v| v.as_str())
            .and_then(|v| v.parse::<f64>().ok());
        let close = obj
            .get("close")
            .and_then(|v| v.as_str())
            .and_then(|v| v.parse::<f64>().ok());

        if let (Some(bucket_start), Some(open), Some(high), Some(low), Some(close)) =
            (ts, open, high, low, close)
        {
            out.push(BarRow {
                bucket_start,
                open,
                high,
                low,
                close,
                trade_count: 0,
                last_event_ts: bucket_start,
            });
        }
    }
    out.sort_by_key(|r| r.bucket_start);
    Ok(out)
}

fn capital_epic_candidates(
    cfg: &HistoryFetchConfig,
    canonical_symbol: &str,
    broker_symbols: &[String],
) -> Vec<String> {
    let mut out = Vec::new();
    let key = canonical_symbol.to_ascii_uppercase();
    if let Some(mapped) = cfg.capital_epic_map.get(&key) {
        out.push(mapped.clone());
    }
    for symbol in broker_symbols {
        if symbol.starts_with("CS.D.") && symbol.ends_with(".IP") {
            out.push(symbol.clone());
        }
    }
    out.push(format!("CS.D.{}.MINI.IP", key));
    out.push(key);
    let mut seen = HashSet::new();
    out.retain(|v| seen.insert(v.clone()));
    out
}

async fn capital_session_headers(
    client: &reqwest::Client,
    cfg: &HistoryFetchConfig,
) -> Result<HeaderMap, String> {
    if cfg.capital_api_key.trim().is_empty()
        || cfg.capital_identifier.trim().is_empty()
        || cfg.capital_password.trim().is_empty()
    {
        return Err("missing Capital credentials".to_string());
    }

    let url = format!(
        "{}/api/v1/session",
        cfg.capital_api_url.trim_end_matches('/')
    );
    let body = serde_json::json!({
        "identifier": cfg.capital_identifier,
        "password": cfg.capital_password,
        "encryptedPassword": false
    });

    let response = client
        .post(url)
        .header("X-CAP-API-KEY", cfg.capital_api_key.clone())
        .header("Content-Type", "application/json")
        .json(&body)
        .send()
        .await
        .map_err(|e| format!("capital session request error: {e}"))?;

    if !response.status().is_success() {
        let status = response.status();
        let body = response.text().await.unwrap_or_default();
        return Err(format!(
            "capital session HTTP {status}: {}",
            body.chars().take(240).collect::<String>()
        ));
    }

    let cst = response
        .headers()
        .get("CST")
        .and_then(|v| v.to_str().ok())
        .unwrap_or("")
        .to_string();
    let security = response
        .headers()
        .get("X-SECURITY-TOKEN")
        .and_then(|v| v.to_str().ok())
        .unwrap_or("")
        .to_string();
    if cst.is_empty() || security.is_empty() {
        return Err("capital session missing CST/X-SECURITY-TOKEN headers".to_string());
    }

    let mut headers = HeaderMap::new();
    headers.insert(
        "X-CAP-API-KEY",
        HeaderValue::from_str(&cfg.capital_api_key)
            .map_err(|e| format!("capital key header error: {e}"))?,
    );
    headers.insert(
        "CST",
        HeaderValue::from_str(&cst).map_err(|e| format!("capital cst header error: {e}"))?,
    );
    headers.insert(
        "X-SECURITY-TOKEN",
        HeaderValue::from_str(&security)
            .map_err(|e| format!("capital security header error: {e}"))?,
    );
    headers.insert("Accept", HeaderValue::from_static("application/json"));
    Ok(headers)
}

async fn fetch_capital_history_bars(
    client: &reqwest::Client,
    cfg: &HistoryFetchConfig,
    command: &ReplayCommand,
    broker_symbols: &[String],
) -> Result<Vec<BarRow>, String> {
    let mut headers = capital_session_headers(client, cfg).await?;
    let from = command.start_ts.format("%Y-%m-%dT%H:%M:%S").to_string();
    let to = (command.end_ts + ChronoDuration::minutes(1))
        .format("%Y-%m-%dT%H:%M:%S")
        .to_string();

    for epic in capital_epic_candidates(cfg, &command.canonical_symbol, broker_symbols) {
        let encoded_epic = urlencoding::encode(&epic);
        let url = format!(
            "{}/api/v1/prices/{}",
            cfg.capital_api_url.trim_end_matches('/'),
            encoded_epic
        );

        let mut response = client
            .get(url.clone())
            .headers(headers.clone())
            .query(&[
                ("resolution", "MINUTE"),
                ("from", from.as_str()),
                ("to", to.as_str()),
                ("max", "1000"),
            ])
            .send()
            .await
            .map_err(|e| format!("capital history request error: {e}"))?;

        if response.status().as_u16() == 401 || response.status().as_u16() == 403 {
            headers = capital_session_headers(client, cfg).await?;
            response = client
                .get(url)
                .headers(headers.clone())
                .query(&[
                    ("resolution", "MINUTE"),
                    ("from", from.as_str()),
                    ("to", to.as_str()),
                    ("max", "1000"),
                ])
                .send()
                .await
                .map_err(|e| format!("capital history retry error: {e}"))?;
        }

        if response.status().as_u16() == 404 {
            continue;
        }
        if !response.status().is_success() {
            let status = response.status();
            let body = response.text().await.unwrap_or_default();
            return Err(format!(
                "capital history HTTP {status}: {}",
                body.chars().take(240).collect::<String>()
            ));
        }

        let payload = response
            .json::<Value>()
            .await
            .map_err(|e| format!("capital history parse error: {e}"))?;
        let Some(prices) = payload.get("prices").and_then(|v| v.as_array()) else {
            continue;
        };
        if prices.is_empty() {
            continue;
        }

        let mut out = Vec::new();
        for price in prices {
            let ts = price
                .get("snapshotTimeUTC")
                .or_else(|| price.get("snapshotTime"))
                .and_then(|v| v.as_str())
                .and_then(parse_utc_minute);
            let open = price.get("openPrice").and_then(parse_capital_price);
            let high = price.get("highPrice").and_then(parse_capital_price);
            let low = price.get("lowPrice").and_then(parse_capital_price);
            let close = price.get("closePrice").and_then(parse_capital_price);

            if let (Some(bucket_start), Some(open), Some(high), Some(low), Some(close)) =
                (ts, open, high, low, close)
            {
                out.push(BarRow {
                    bucket_start,
                    open,
                    high,
                    low,
                    close,
                    trade_count: 0,
                    last_event_ts: bucket_start,
                });
            }
        }
        if !out.is_empty() {
            out.sort_by_key(|r| r.bucket_start);
            return Ok(out);
        }
    }

    Ok(Vec::new())
}

async fn fetch_venue_history_bars(
    cfg: &HistoryFetchConfig,
    command: &ReplayCommand,
    broker_symbols: &[String],
) -> Result<Vec<BarRow>, String> {
    fn venue_chunk_minutes(venue: &str) -> i64 {
        match venue {
            // OANDA supports larger windows, keep room for API response limits.
            "oanda" => 4_000,
            // Coinbase exchange/public candle routes are usually a few hundred rows per call.
            "coinbase" => 300,
            // Capital allows up to ~1000 rows at M1.
            "capital" => 900,
            _ => 300,
        }
    }

    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(cfg.timeout_secs))
        .build()
        .map_err(|e| format!("history client build error: {e}"))?;

    let chunk_minutes = venue_chunk_minutes(&command.venue).max(1);
    let mut cursor = minute_bucket(command.start_ts);
    let end = minute_bucket(command.end_ts);

    let mut by_bucket: HashMap<DateTime<Utc>, BarRow> = HashMap::new();
    while cursor <= end {
        let window_end = std::cmp::min(cursor + ChronoDuration::minutes(chunk_minutes - 1), end);
        let sub_command = ReplayCommand {
            replay_id: command.replay_id,
            venue: command.venue.clone(),
            canonical_symbol: command.canonical_symbol.clone(),
            timeframe: command.timeframe.clone(),
            start_ts: cursor,
            end_ts: window_end,
            dry_run: command.dry_run,
        };

        let window_rows = match command.venue.as_str() {
            "oanda" => fetch_oanda_history_bars(&client, cfg, &sub_command, broker_symbols).await?,
            "coinbase" => fetch_coinbase_history_bars(&client, cfg, &sub_command).await?,
            "capital" => {
                fetch_capital_history_bars(&client, cfg, &sub_command, broker_symbols).await?
            }
            _ => {
                return Err(format!(
                    "venue history adapter not implemented for {}",
                    command.venue
                ))
            }
        };

        for row in window_rows {
            by_bucket.insert(row.bucket_start, row);
        }
        cursor = window_end + ChronoDuration::minutes(1);
    }

    let mut out = by_bucket.into_values().collect::<Vec<_>>();
    out.sort_by_key(|r| r.bucket_start);
    Ok(out)
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
        dry_run: payload
            .get("dry_run")
            .and_then(|v| v.as_bool())
            .unwrap_or(false),
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
          enqueue_count INT NOT NULL DEFAULT 0,
          last_enqueued_at TIMESTAMPTZ,
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

        ALTER TABLE backfill_jobs
          ADD COLUMN IF NOT EXISTS enqueue_count INT NOT NULL DEFAULT 0;

        ALTER TABLE backfill_jobs
          ADD COLUMN IF NOT EXISTS last_enqueued_at TIMESTAMPTZ;
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

    if let Some(mapped) = registry.get(&(
        venue.to_ascii_lowercase(),
        canonical_symbol.to_ascii_uppercase(),
    )) {
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
    history_cfg: &HistoryFetchConfig,
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
        update_replay_audit(conn, command.replay_id, "failed", 0, Some("invalid range")).await?;
        return Ok(());
    }

    let registry_key = (
        command.venue.to_ascii_lowercase(),
        command.canonical_symbol.to_ascii_uppercase(),
    );
    if !registry.contains_key(&registry_key) {
        update_backfill_job_status(conn, command, "failed_unknown_market").await?;
        update_replay_audit(
            conn,
            command.replay_id,
            "failed",
            0,
            Some("market is not mapped in symbol registry"),
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

    let broker_symbols =
        candidate_broker_symbols(registry, &command.venue, &command.canonical_symbol);
    let bars = fetch_aggregated_bars(conn, command, &broker_symbols).await?;
    let mut written = upsert_ohlcv_bars(conn, command, &bars).await?;

    if history_cfg.enabled {
        let complete_after_ticks = is_range_complete(conn, command).await?;
        if !complete_after_ticks {
            match fetch_venue_history_bars(history_cfg, command, &broker_symbols).await {
                Ok(history_bars) => {
                    if !history_bars.is_empty() {
                        written += upsert_ohlcv_bars(conn, command, &history_bars).await?;
                    }
                }
                Err(err) => {
                    eprintln!(
                        "replay-controller history fetch failed venue={} symbol={} range={}..{} error={}",
                        command.venue,
                        command.canonical_symbol,
                        command.start_ts,
                        command.end_ts,
                        err
                    );
                }
            }
        }
    }

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

async fn run_worker(
    worker_id: usize,
    service_name: &'static str,
    brokers: &str,
    input_topic: &str,
    group_id: &str,
    db_dsn: &str,
    registry: &HashMap<(String, String), Vec<String>>,
    history_cfg: &HistoryFetchConfig,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let (conn, connection) = tokio_postgres::connect(db_dsn, NoTls).await?;
    tokio::spawn(async move {
        if let Err(e) = connection.await {
            eprintln!("postgres connection error (worker={}): {e}", worker_id);
        }
    });

    let consumer: StreamConsumer = ClientConfig::new()
        .set("bootstrap.servers", brokers)
        .set("group.id", group_id)
        .set(
            "client.id",
            &format!("nitra-replay-controller-worker-{}", worker_id),
        )
        .set("enable.auto.commit", "false")
        .set("auto.offset.reset", "earliest")
        .create()?;
    consumer.subscribe(&[input_topic])?;

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
            let command_err = process_replay_command(&conn, &command, registry, history_cfg)
                .await
                .err()
                .map(|e| e.to_string());
            if let Some(msg) = command_err {
                let _ =
                    update_replay_audit(&conn, command.replay_id, "failed", 0, Some(&msg)).await;
                eprintln!(
                    "replay-controller worker={} command failed replay_id={} error={}",
                    worker_id, command.replay_id, msg
                );
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

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let service_name = "replay_controller";
    let brokers = env_or("KAFKA_BROKERS", "kafka:9092");
    let input_topic = env_or("REPLAY_INPUT_TOPIC", "replay.commands");
    let group_id = env_or("REPLAY_GROUP_ID", "nitra-replay-controller-v1");
    let db_dsn = env_or(
        "DATABASE_URL",
        "postgresql://trading:trading@timescaledb:5432/trading",
    );
    let registry_path = env_or("REPLAY_SYMBOL_REGISTRY_PATH", "/etc/nitra/registry.v1.json");
    let worker_count = env_u64_or("REPLAY_WORKER_COUNT", 4).clamp(1, 16) as usize;
    let history_cfg = history_fetch_config();

    let registry = load_symbol_registry(&registry_path);

    let (conn, connection) = tokio_postgres::connect(&db_dsn, NoTls).await?;
    tokio::spawn(async move {
        if let Err(e) = connection.await {
            eprintln!("postgres connection error: {e}");
        }
    });

    ensure_tables(&conn).await?;

    let mut workers = JoinSet::new();
    for worker_id in 0..worker_count {
        let brokers = brokers.clone();
        let input_topic = input_topic.clone();
        let group_id = group_id.clone();
        let db_dsn = db_dsn.clone();
        let registry = registry.clone();
        let history_cfg = history_cfg.clone();
        workers.spawn(async move {
            run_worker(
                worker_id,
                service_name,
                &brokers,
                &input_topic,
                &group_id,
                &db_dsn,
                &registry,
                &history_cfg,
            )
            .await
        });
    }

    while let Some(next) = workers.join_next().await {
        match next {
            Ok(Ok(())) => {}
            Ok(Err(err)) => return Err(err),
            Err(err) => return Err(Box::new(err)),
        }
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

    #[test]
    fn capital_epic_map_parses_json() {
        let parsed = parse_capital_epic_map(r#"{"EURUSD":"CS.D.EURUSD.MINI.IP"}"#);
        assert_eq!(
            parsed.get("EURUSD"),
            Some(&"CS.D.EURUSD.MINI.IP".to_string())
        );
    }

    #[test]
    fn coinbase_symbol_formatting() {
        assert_eq!(symbol_for_coinbase("BTCUSD"), "BTC-USD");
        assert_eq!(symbol_for_coinbase("BTC-USD"), "BTC-USD");
    }

    #[test]
    fn oanda_symbol_falls_back_to_usd_suffix_variant() {
        let cfg = HistoryFetchConfig {
            enabled: true,
            timeout_secs: 8,
            oanda_rest_url: String::new(),
            oanda_token: String::new(),
            oanda_instrument_map: HashMap::new(),
            coinbase_rest_url: String::new(),
            coinbase_public_rest_url: String::new(),
            coinbase_user_agent: String::new(),
            capital_api_url: String::new(),
            capital_api_key: String::new(),
            capital_identifier: String::new(),
            capital_password: String::new(),
            capital_epic_map: HashMap::new(),
        };
        assert_eq!(symbol_for_oanda(&cfg, "US30", &[]), "US30_USD");
        assert_eq!(symbol_for_oanda(&cfg, "NAS100", &[]), "NAS100_USD");
    }

    #[test]
    fn oanda_symbol_prefers_explicit_map() {
        let mut map = HashMap::new();
        map.insert("US30".to_string(), "US30_CFD".to_string());
        let cfg = HistoryFetchConfig {
            enabled: true,
            timeout_secs: 8,
            oanda_rest_url: String::new(),
            oanda_token: String::new(),
            oanda_instrument_map: map,
            coinbase_rest_url: String::new(),
            coinbase_public_rest_url: String::new(),
            coinbase_user_agent: String::new(),
            capital_api_url: String::new(),
            capital_api_key: String::new(),
            capital_identifier: String::new(),
            capital_password: String::new(),
            capital_epic_map: HashMap::new(),
        };
        assert_eq!(symbol_for_oanda(&cfg, "US30", &[]), "US30_CFD");
    }
}
