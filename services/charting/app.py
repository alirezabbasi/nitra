import os
import json
import urllib.parse
import urllib.request
import urllib.error
import socket
import threading
from pathlib import Path
from datetime import datetime, timezone, timedelta

import psycopg
import uvicorn
from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


def env(name: str, default: str) -> str:
    return os.getenv(name, default)


def int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def db_url() -> str:
    from_env = os.getenv("DATABASE_URL")
    if from_env:
        return from_env
    user = env("POSTGRES_USER", "trading")
    password = env("POSTGRES_PASSWORD", "trading")
    database = env("POSTGRES_DB", "trading")
    host = env("POSTGRES_HOST", "timescaledb")
    port = env("POSTGRES_PORT", "5432")
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


DEFAULT_TIMEFRAME = env("CHARTING_TIMEFRAME", "1m")
DEFAULT_LIMIT = int_env("CHARTING_DEFAULT_LIMIT", 300)
DEFAULT_REFRESH_SECS = int_env("CHARTING_REFRESH_SECS", 5)
VENUE_FETCH_TIMEOUT_SECS = max(3, int_env("CHARTING_VENUE_FETCH_TIMEOUT_SECS", 8))
VENUE_FETCH_MAX_ERRORS = max(1, int_env("CHARTING_VENUE_FETCH_MAX_ERRORS", 3))
OANDA_REST_URL = env("OANDA_REST_URL", "https://api-fxpractice.oanda.com")
COINBASE_REST_URL = env("COINBASE_REST_URL", "https://api.exchange.coinbase.com")
COINBASE_PUBLIC_REST_URL = env("COINBASE_PUBLIC_REST_URL", "https://api.coinbase.com")

CRYPTO_BASES = {
    "BTC",
    "ETH",
    "SOL",
    "ADA",
    "XRP",
    "LTC",
    "DOGE",
    "BNB",
    "AVAX",
    "DOT",
    "LINK",
}

_CAPITAL_SESSION_LOCK = threading.Lock()
_CAPITAL_SESSION_HEADERS: dict[str, str] = {}
_CAPITAL_SESSION_EXPIRY: datetime | None = None

app = FastAPI(title="nitra-charting")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "charting"}


@app.get("/api/v1/config")
def charting_config() -> dict:
    return {
        "default_timeframe": DEFAULT_TIMEFRAME,
        "default_limit": DEFAULT_LIMIT,
        "default_refresh_secs": DEFAULT_REFRESH_SECS,
    }


def broker_symbol_candidates(venue: str, symbol: str) -> list[str]:
    out = [symbol]
    if venue.lower() == "oanda" and len(symbol) == 6 and symbol.isalpha():
        out.append(f"{symbol[:3]}_{symbol[3:]}")
    dedup: list[str] = []
    for item in out:
        if item not in dedup:
            dedup.append(item)
    return dedup


def canonical_window_90d() -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    end_dt = now.replace(second=0, microsecond=0) - timedelta(minutes=1)
    start_dt = end_dt - timedelta(days=90) + timedelta(minutes=1)
    return start_dt, end_dt


def is_crypto_symbol(symbol: str) -> bool:
    upper = symbol.upper()
    if len(upper) >= 6 and upper.endswith("USD"):
        return upper[:-3] in CRYPTO_BASES
    if len(upper) >= 7 and upper.endswith("USDT"):
        return upper[:-4] in CRYPTO_BASES
    if len(upper) >= 7 and upper.endswith("USDC"):
        return upper[:-4] in CRYPTO_BASES
    return False


def fx_weekday_only_policy(venue: str, symbol: str) -> bool:
    return venue.lower() in {"oanda", "capital"} and not is_crypto_symbol(symbol)


def expected_minutes(start_dt: datetime, end_dt: datetime, *, weekday_only: bool) -> int:
    if end_dt < start_dt:
        return 0
    if not weekday_only:
        return int((end_dt - start_dt).total_seconds() // 60) + 1
    total = 0
    cursor = start_dt
    while cursor <= end_dt:
        if cursor.isoweekday() <= 5:
            total += 1
        cursor += timedelta(minutes=1)
    return total


def merge_missing_minutes(minutes: list[datetime]) -> list[tuple[datetime, datetime]]:
    if not minutes:
        return []
    ranges: list[tuple[datetime, datetime]] = []
    start = minutes[0]
    prev = minutes[0]
    for bucket in minutes[1:]:
        if bucket == prev + timedelta(minutes=1):
            prev = bucket
            continue
        ranges.append((start, prev))
        start = bucket
        prev = bucket
    ranges.append((start, prev))
    return ranges


def upsert_bars(conn: psycopg.Connection, venue: str, symbol: str, bars: list[tuple]) -> int:
    if not bars:
        return 0
    upsert_query = """
    INSERT INTO ohlcv_bar (
      venue, canonical_symbol, timeframe, bucket_start,
      open, high, low, close, volume, trade_count, last_event_ts
    ) VALUES (%s,%s,'1m',%s,%s,%s,%s,%s,%s,%s,%s)
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
    """
    payload = [
        (
            venue,
            symbol,
            bucket_start,
            float(o),
            float(h),
            float(l),
            float(c),
            None,
            int(trade_count),
            last_event_ts,
        )
        for bucket_start, o, h, l, c, trade_count, last_event_ts in bars
        if None not in (bucket_start, o, h, l, c, last_event_ts)
    ]
    with conn.cursor() as cur:
        cur.executemany(upsert_query, payload)
    return len(payload)


def upsert_from_raw_ticks(
    conn: psycopg.Connection,
    venue: str,
    symbol: str,
    broker_symbols: list[str],
    start_dt: datetime,
    end_dt: datetime,
) -> tuple[int, int, datetime | None, datetime | None]:
    end_exclusive = end_dt + timedelta(minutes=1)
    coverage_query = """
    SELECT
      MIN(event_ts_received) AS min_ts,
      MAX(event_ts_received) AS max_ts,
      COUNT(*) AS tick_count
    FROM raw_tick
    WHERE venue = %s
      AND broker_symbol = ANY(%s)
      AND event_ts_received >= %s
      AND event_ts_received < %s
      AND COALESCE(mid, (bid + ask) / 2.0, last) IS NOT NULL
    """
    bars_query = """
    WITH ticks AS (
      SELECT
        date_trunc('minute', event_ts_received) AS bucket_start,
        event_ts_received AS ts,
        COALESCE(mid, (bid + ask) / 2.0, last) AS price
      FROM raw_tick
      WHERE venue = %s
        AND broker_symbol = ANY(%s)
        AND event_ts_received >= %s
        AND event_ts_received < %s
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
    """
    with conn.cursor() as cur:
        cur.execute(coverage_query, (venue, broker_symbols, start_dt, end_exclusive))
        min_ts, max_ts, tick_count = cur.fetchone()
        cur.execute(bars_query, (venue, broker_symbols, start_dt, end_exclusive))
        bars = cur.fetchall()
    upserted = upsert_bars(conn, venue, symbol, bars)
    return upserted, int(tick_count or 0), min_ts, max_ts


def fetch_missing_minutes(
    conn: psycopg.Connection,
    venue: str,
    symbol: str,
    start_dt: datetime,
    end_dt: datetime,
    *,
    weekday_only: bool,
) -> list[datetime]:
    include_weekends = not weekday_only
    query = """
    WITH expected AS (
      SELECT gs AS bucket_start
      FROM generate_series(%s::timestamptz, %s::timestamptz, interval '1 minute') AS gs
      WHERE (%s::boolean OR EXTRACT(ISODOW FROM gs) <= 5)
    ),
    actual AS (
      SELECT bucket_start
      FROM ohlcv_bar
      WHERE venue = %s
        AND canonical_symbol = %s
        AND timeframe = '1m'
        AND bucket_start >= %s
        AND bucket_start <= %s
    )
    SELECT e.bucket_start
    FROM expected e
    LEFT JOIN actual a ON a.bucket_start = e.bucket_start
    WHERE a.bucket_start IS NULL
    ORDER BY e.bucket_start
    """
    with conn.cursor() as cur:
        cur.execute(query, (start_dt, end_dt, include_weekends, venue, symbol, start_dt, end_dt))
        rows = cur.fetchall()
    return [row[0] for row in rows]


def oanda_instrument(symbol: str) -> str:
    if len(symbol) == 6 and symbol.isalpha():
        return f"{symbol[:3]}_{symbol[3:]}"
    return symbol


def coinbase_product(symbol: str) -> str:
    if len(symbol) == 6 and symbol.isalpha():
        return f"{symbol[:3]}-{symbol[3:]}"
    return symbol


def capital_base_url() -> str:
    return env("CAPITAL_API_URL", "https://api-capital.backend-capital.com").rstrip("/")


def capital_epic_candidates(symbol: str) -> list[str]:
    candidates = []
    mapping_raw = os.getenv("CAPITAL_EPIC_MAP", "").strip()
    if mapping_raw:
        try:
            parsed = json.loads(mapping_raw)
            if isinstance(parsed, dict):
                mapped = parsed.get(symbol.upper())
                if isinstance(mapped, str) and mapped.strip():
                    candidates.append(mapped.strip())
        except Exception:
            pass
    candidates.append(f"CS.D.{symbol.upper()}.MINI.IP")
    candidates.append(symbol.upper())
    dedup: list[str] = []
    for item in candidates:
        if item not in dedup:
            dedup.append(item)
    return dedup


def capital_session_headers(force_refresh: bool = False) -> dict[str, str]:
    global _CAPITAL_SESSION_HEADERS, _CAPITAL_SESSION_EXPIRY
    now = datetime.now(timezone.utc)
    with _CAPITAL_SESSION_LOCK:
        if (
            not force_refresh
            and _CAPITAL_SESSION_HEADERS
            and _CAPITAL_SESSION_EXPIRY
            and _CAPITAL_SESSION_EXPIRY > now
        ):
            return dict(_CAPITAL_SESSION_HEADERS)

        api_key = os.getenv("CAPITAL_API_KEY", "").strip()
        identifier = os.getenv("CAPITAL_IDENTIFIER", "").strip()
        password = os.getenv("CAPITAL_API_PASSWORD", "").strip()
        if not (api_key and identifier and password):
            raise RuntimeError("capital credentials missing: CAPITAL_API_KEY/CAPITAL_IDENTIFIER/CAPITAL_API_PASSWORD")

        url = f"{capital_base_url()}/api/v1/session"
        body = json.dumps(
            {
                "identifier": identifier,
                "password": password,
                "encryptedPassword": False,
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-CAP-API-KEY": api_key,
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=VENUE_FETCH_TIMEOUT_SECS) as resp:
            cst = resp.headers.get("CST", "")
            security = resp.headers.get("X-SECURITY-TOKEN", "")
        if not cst or not security:
            raise RuntimeError("capital session established without CST/X-SECURITY-TOKEN headers")

        _CAPITAL_SESSION_HEADERS = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-CAP-API-KEY": api_key,
            "CST": cst,
            "X-SECURITY-TOKEN": security,
        }
        _CAPITAL_SESSION_EXPIRY = now + timedelta(minutes=9)
        return dict(_CAPITAL_SESSION_HEADERS)


def parse_capital_price(price_obj: object) -> float | None:
    if isinstance(price_obj, (int, float)):
        return float(price_obj)
    if not isinstance(price_obj, dict):
        return None
    bid = price_obj.get("bid")
    ask = price_obj.get("ask")
    if isinstance(bid, (int, float)) and isinstance(ask, (int, float)):
        return (float(bid) + float(ask)) / 2.0
    if isinstance(bid, (int, float)):
        return float(bid)
    if isinstance(ask, (int, float)):
        return float(ask)
    return None


def parse_iso_ts(raw: str) -> datetime:
    normalized = raw.replace("Z", "+00:00")
    ts = datetime.fromisoformat(normalized)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc).replace(second=0, microsecond=0)


def fetch_capital_range(symbol: str, start_dt: datetime, end_dt: datetime) -> list[tuple]:
    from_str = start_dt.strftime("%Y-%m-%dT%H:%M:%S")
    to_str = (end_dt + timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%S")
    for epic in capital_epic_candidates(symbol):
        headers = capital_session_headers(force_refresh=False)
        params = urllib.parse.urlencode(
            {
                "resolution": "MINUTE",
                "from": from_str,
                "to": to_str,
                "max": "1000",
            }
        )
        url = f"{capital_base_url()}/api/v1/prices/{urllib.parse.quote(epic, safe='')}?{params}"
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=VENUE_FETCH_TIMEOUT_SECS) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in {401, 403}:
                # Session may have expired; retry once with forced session refresh.
                headers = capital_session_headers(force_refresh=True)
                req = urllib.request.Request(url, headers=headers, method="GET")
                with urllib.request.urlopen(req, timeout=VENUE_FETCH_TIMEOUT_SECS) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
            elif exc.code == 404:
                continue
            else:
                raise

        prices = payload.get("prices", [])
        if not prices:
            continue
        bars: list[tuple] = []
        for item in prices:
            if not isinstance(item, dict):
                continue
            ts_raw = item.get("snapshotTimeUTC") or item.get("snapshotTime")
            if not isinstance(ts_raw, str) or not ts_raw.strip():
                continue
            try:
                ts = parse_iso_ts(ts_raw.strip())
            except Exception:
                continue

            open_ = parse_capital_price(item.get("openPrice"))
            high = parse_capital_price(item.get("highPrice"))
            low = parse_capital_price(item.get("lowPrice"))
            close = parse_capital_price(item.get("closePrice"))
            if None in (open_, high, low, close):
                continue
            bars.append((ts, float(open_), float(high), float(low), float(close), 0, ts))
        if bars:
            return bars
    return []


def chunk_range(start_dt: datetime, end_dt: datetime, chunk_minutes: int) -> list[tuple[datetime, datetime]]:
    out: list[tuple[datetime, datetime]] = []
    cursor = start_dt
    while cursor <= end_dt:
        chunk_end = min(end_dt, cursor + timedelta(minutes=chunk_minutes - 1))
        out.append((cursor, chunk_end))
        cursor = chunk_end + timedelta(minutes=1)
    return out


def fetch_oanda_range(symbol: str, start_dt: datetime, end_dt: datetime) -> list[tuple]:
    token = os.getenv("OANDA_API_TOKEN", "").strip()
    if not token:
        return []
    base = OANDA_REST_URL.rstrip("/")
    instrument = oanda_instrument(symbol)
    params = urllib.parse.urlencode(
        {
            "granularity": "M1",
            "price": "M",
            "from": start_dt.isoformat().replace("+00:00", "Z"),
            "to": (end_dt + timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
            "includeFirst": "true",
        }
    )
    url = f"{base}/v3/instruments/{instrument}/candles?{params}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept-Datetime-Format": "RFC3339",
            "Content-Type": "application/json",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=VENUE_FETCH_TIMEOUT_SECS) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    candles = payload.get("candles", [])
    bars: list[tuple] = []
    for candle in candles:
        if not candle.get("complete", False):
            continue
        mid = candle.get("mid") or {}
        ts_raw = candle.get("time")
        if ts_raw is None:
            continue
        ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00")).astimezone(timezone.utc).replace(second=0, microsecond=0)
        o = mid.get("o")
        h = mid.get("h")
        l = mid.get("l")
        c = mid.get("c")
        if None in (o, h, l, c):
            continue
        bars.append((ts, float(o), float(h), float(l), float(c), 0, ts))
    return bars


def fetch_coinbase_range(symbol: str, start_dt: datetime, end_dt: datetime) -> list[tuple]:
    base = COINBASE_REST_URL.rstrip("/")
    product = coinbase_product(symbol)
    params = urllib.parse.urlencode(
        {
            "granularity": "60",
            "start": start_dt.isoformat().replace("+00:00", "Z"),
            "end": (end_dt + timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
        }
    )
    url = f"{base}/products/{product}/candles?{params}"
    req = urllib.request.Request(url, headers={"Content-Type": "application/json"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=VENUE_FETCH_TIMEOUT_SECS) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        bars: list[tuple] = []
        # Coinbase Exchange returns [time, low, high, open, close, volume]
        for row in payload:
            if not isinstance(row, list) or len(row) < 5:
                continue
            ts = datetime.fromtimestamp(int(row[0]), tz=timezone.utc).replace(second=0, microsecond=0)
            low = float(row[1])
            high = float(row[2])
            open_ = float(row[3])
            close = float(row[4])
            bars.append((ts, open_, high, low, close, 0, ts))
        bars.sort(key=lambda item: item[0])
        if bars:
            return bars
    except urllib.error.HTTPError as exc:
        if exc.code not in {403, 429, 500, 503}:
            raise

    # Fallback: Coinbase Advanced Trade public candles endpoint.
    public_base = COINBASE_PUBLIC_REST_URL.rstrip("/")
    params_v3 = urllib.parse.urlencode(
        {
            "granularity": "ONE_MINUTE",
            "start": str(int(start_dt.timestamp())),
            "end": str(int((end_dt + timedelta(minutes=1)).timestamp())),
            "limit": "350",
        }
    )
    v3_url = f"{public_base}/api/v3/brokerage/market/products/{product}/candles?{params_v3}"
    v3_req = urllib.request.Request(
        v3_url,
        headers={"Content-Type": "application/json", "Cache-Control": "no-cache"},
        method="GET",
    )
    with urllib.request.urlopen(v3_req, timeout=VENUE_FETCH_TIMEOUT_SECS) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    candles = payload.get("candles", [])
    bars: list[tuple] = []
    for item in candles:
        if not isinstance(item, dict):
            continue
        start_raw = item.get("start")
        low_raw = item.get("low")
        high_raw = item.get("high")
        open_raw = item.get("open")
        close_raw = item.get("close")
        if None in (start_raw, low_raw, high_raw, open_raw, close_raw):
            continue
        ts = datetime.fromtimestamp(int(start_raw), tz=timezone.utc).replace(second=0, microsecond=0)
        bars.append((ts, float(open_raw), float(high_raw), float(low_raw), float(close_raw), 0, ts))
    bars.sort(key=lambda item: item[0])
    return bars


def fetch_from_venue(venue: str, symbol: str, ranges: list[tuple[datetime, datetime]]) -> tuple[int, str]:
    # Keep each venue request within provider limits (Coinbase candles API is strict: max 300).
    chunk_minutes_map = {
        "oanda": 4500,
        "coinbase": 300,
        "capital": 1000,
    }
    chunk_minutes = chunk_minutes_map.get(venue, 300)
    fetched = 0
    errors: list[str] = []
    failed_calls = 0
    for start_dt, end_dt in ranges:
        chunks = chunk_range(start_dt, end_dt, chunk_minutes=chunk_minutes)
        for chunk_start, chunk_end in chunks:
            try:
                if venue == "oanda":
                    bars = fetch_oanda_range(symbol, chunk_start, chunk_end)
                elif venue == "coinbase":
                    bars = fetch_coinbase_range(symbol, chunk_start, chunk_end)
                elif venue == "capital":
                    bars = fetch_capital_range(symbol, chunk_start, chunk_end)
                else:
                    return fetched, f"venue adapter not implemented for {venue}"
                if bars:
                    failed_calls = 0
            except urllib.error.HTTPError as exc:
                body = ""
                try:
                    body = exc.read().decode("utf-8", errors="ignore")
                except Exception:
                    body = ""
                errors.append(
                    f"{chunk_start.isoformat()}..{chunk_end.isoformat()}: HTTP {exc.code} {body[:240]}"
                )
                failed_calls += 1
                if failed_calls >= VENUE_FETCH_MAX_ERRORS:
                    return fetched, f"aborted after {failed_calls} venue fetch errors: {'; '.join(errors[:3])}"
                continue
            except urllib.error.URLError as exc:
                reason = getattr(exc, "reason", exc)
                errors.append(
                    f"{chunk_start.isoformat()}..{chunk_end.isoformat()}: URL error {reason}"
                )
                failed_calls += 1
                if failed_calls >= VENUE_FETCH_MAX_ERRORS:
                    return fetched, f"aborted after {failed_calls} venue fetch errors: {'; '.join(errors[:3])}"
                continue
            except socket.timeout:
                errors.append(f"{chunk_start.isoformat()}..{chunk_end.isoformat()}: socket timeout")
                failed_calls += 1
                if failed_calls >= VENUE_FETCH_MAX_ERRORS:
                    return fetched, f"aborted after {failed_calls} venue fetch errors: {'; '.join(errors[:3])}"
                continue
            except Exception as exc:
                errors.append(f"{chunk_start.isoformat()}..{chunk_end.isoformat()}: {exc}")
                failed_calls += 1
                if failed_calls >= VENUE_FETCH_MAX_ERRORS:
                    return fetched, f"aborted after {failed_calls} venue fetch errors: {'; '.join(errors[:3])}"
                continue
            fetched += len(bars)
            if bars:
                with psycopg.connect(db_url()) as conn:
                    upsert_bars(conn, venue, symbol, bars)
                    conn.commit()
    return fetched, "; ".join(errors[:3])


@app.post("/api/v1/backfill/90d")
def backfill_90d(
    venue: str = Body(min_length=1, max_length=64),
    symbol: str = Body(min_length=1, max_length=64),
) -> dict:
    venue_norm = venue.strip().lower()
    symbol_norm = symbol.strip().upper()
    weekday_only = fx_weekday_only_policy(venue_norm, symbol_norm)
    start_dt, end_dt = canonical_window_90d()
    broker_symbols = broker_symbol_candidates(venue_norm, symbol_norm)
    requested_minutes = expected_minutes(start_dt, end_dt, weekday_only=weekday_only)
    first_missing_after = []
    missing_ranges: list[tuple[datetime, datetime]] = []
    upserted_from_ticks = 0
    source_tick_count = 0
    min_ts = None
    max_ts = None

    with psycopg.connect(db_url()) as conn:
        upserted_from_ticks, source_tick_count, min_ts, max_ts = upsert_from_raw_ticks(
            conn, venue_norm, symbol_norm, broker_symbols, start_dt, end_dt
        )
        conn.commit()

        missing_before = fetch_missing_minutes(
            conn, venue_norm, symbol_norm, start_dt, end_dt, weekday_only=weekday_only
        )
        missing_ranges = merge_missing_minutes(missing_before)
        missing_before_count = len(missing_before)

    venue_fetch_rows = 0
    venue_fetch_error = ""
    if missing_ranges:
        venue_fetch_rows, venue_fetch_error = fetch_from_venue(venue_norm, symbol_norm, missing_ranges)
        if venue_fetch_rows == 0 and not venue_fetch_error:
            venue_fetch_error = "venue returned no candles for missing ranges (likely non-trading windows or unavailable history)"

    with psycopg.connect(db_url()) as conn:
        missing_after = fetch_missing_minutes(
            conn, venue_norm, symbol_norm, start_dt, end_dt, weekday_only=weekday_only
        )
        first_missing_after = [m.isoformat() for m in missing_after[:5]]

    complete = len(missing_after) == 0
    covered_minutes = requested_minutes - len(missing_after)
    return {
        "venue": venue_norm,
        "symbol": symbol_norm,
        "requested_window": {"start": start_dt.isoformat(), "end": end_dt.isoformat()},
        "requested_minutes": requested_minutes,
        "source_tick_count": source_tick_count,
        "source_tick_range": {
            "min_ts": min_ts.isoformat() if min_ts else None,
            "max_ts": max_ts.isoformat() if max_ts else None,
        },
        "bars_upserted_from_ticks": upserted_from_ticks,
        "venue_rows_fetched": venue_fetch_rows,
        "missing_before_fetch_count": missing_before_count,
        "missing_after_fetch_count": len(missing_after),
        "coverage_ratio": (covered_minutes / requested_minutes) if requested_minutes > 0 else 0.0,
        "complete_90d_1m": complete,
        "continuity_policy": "weekday_only_for_fx" if weekday_only else "all_minutes",
        "first_missing_minutes": first_missing_after if not complete else [],
        "venue_fetch_error": venue_fetch_error,
        "note": "Strict coverage mode: backfill rebuilds from raw_tick, then fetches missing required 1m windows from venue adapters. For FX venues, closed-market weekend minutes are excluded from required continuity.",
    }


@app.get("/api/v1/markets/available")
def markets_available(timeframe: str = Query(default=DEFAULT_TIMEFRAME, min_length=1, max_length=16)) -> dict:
    query = """
    SELECT
      venue,
      canonical_symbol,
      timeframe,
      MAX(bucket_start) AS last_bar_ts,
      COUNT(*) AS bar_count
    FROM ohlcv_bar
    WHERE timeframe = %s
    GROUP BY venue, canonical_symbol, timeframe
    ORDER BY venue, canonical_symbol
    """
    with psycopg.connect(db_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(query, (timeframe,))
            rows = cur.fetchall()

    markets = []
    for venue, symbol, row_timeframe, last_bar_ts, bar_count in rows:
        markets.append(
            {
                "venue": venue,
                "symbol": symbol,
                "timeframe": row_timeframe,
                "last_bar_ts": last_bar_ts.isoformat() if last_bar_ts else None,
                "bar_count": int(bar_count),
            }
        )

    return {"timeframe": timeframe, "markets": markets}


@app.get("/api/v1/bars/hot")
def bars_hot(
    venue: str = Query(min_length=1, max_length=64),
    symbol: str = Query(min_length=1, max_length=64),
    timeframe: str = Query(default=DEFAULT_TIMEFRAME, min_length=1, max_length=16),
    limit: int = Query(default=DEFAULT_LIMIT, ge=10, le=3000),
) -> dict:
    query = """
    SELECT
      bucket_start,
      open,
      high,
      low,
      close,
      COALESCE(volume, 0),
      COALESCE(trade_count, 0)
    FROM ohlcv_bar
    WHERE venue = %s
      AND canonical_symbol = %s
      AND timeframe = %s
    ORDER BY bucket_start DESC
    LIMIT %s
    """

    with psycopg.connect(db_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(query, (venue, symbol, timeframe, limit))
            rows = cur.fetchall()

    bars = _rows_to_bars(rows)

    return {
        "venue": venue,
        "symbol": symbol,
        "timeframe": timeframe,
        "bars": bars,
    }


def _rows_to_bars(rows: list[tuple]) -> list[dict]:
    out: list[dict] = []
    for bucket_start, o, h, l, c, volume, trade_count in reversed(rows):
        if None in (o, h, l, c):
            continue
        out.append(
            {
                "time": int(bucket_start.timestamp()),
                "open": float(o),
                "high": float(h),
                "low": float(l),
                "close": float(c),
                "volume": float(volume),
                "trade_count": int(trade_count),
            }
        )
    return out


@app.get("/api/v1/bars/history")
def bars_history(
    venue: str = Query(min_length=1, max_length=64),
    symbol: str = Query(min_length=1, max_length=64),
    timeframe: str = Query(default=DEFAULT_TIMEFRAME, min_length=1, max_length=16),
    before_s: int = Query(ge=0),
    limit: int = Query(default=500, ge=10, le=3000),
) -> dict:
    before_dt = datetime.fromtimestamp(before_s, tz=timezone.utc)
    query = """
    SELECT
      bucket_start,
      open,
      high,
      low,
      close,
      COALESCE(volume, 0),
      COALESCE(trade_count, 0)
    FROM ohlcv_bar
    WHERE venue = %s
      AND canonical_symbol = %s
      AND timeframe = %s
      AND bucket_start < %s
    ORDER BY bucket_start DESC
    LIMIT %s
    """

    with psycopg.connect(db_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(query, (venue, symbol, timeframe, before_dt, limit + 1))
            rows = cur.fetchall()

    has_more = len(rows) > limit
    bars = _rows_to_bars(rows[:limit])
    return {
        "venue": venue,
        "symbol": symbol,
        "timeframe": timeframe,
        "bars": bars,
        "has_more": has_more,
    }


@app.get("/api/v1/ticks/hot")
def ticks_hot(
    venue: str = Query(min_length=1, max_length=64),
    symbol: str = Query(min_length=1, max_length=64),
    since_ms: int | None = Query(default=None, ge=0),
    limit: int = Query(default=2000, ge=1, le=5000),
) -> dict:
    since_seconds = (since_ms / 1000.0) if since_ms is not None else None
    query = """
    SELECT
      EXTRACT(EPOCH FROM event_ts_received) * 1000.0 AS ts_ms,
      COALESCE(mid, (bid + ask) / 2.0, last) AS price
    FROM raw_tick
    WHERE venue = %s
      AND broker_symbol = %s
      AND COALESCE(mid, (bid + ask) / 2.0, last) IS NOT NULL
      AND (%s::double precision IS NULL OR event_ts_received > to_timestamp(%s::double precision))
    ORDER BY event_ts_received DESC
    LIMIT %s
    """
    with psycopg.connect(db_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(query, (venue, symbol, since_seconds, since_seconds, limit))
            rows = cur.fetchall()

    ticks = []
    # Query is DESC for freshness; client expects ASC time order.
    for ts_ms, price in reversed(rows):
        if ts_ms is None or price is None:
            continue
        ticks.append(
            {
                "ts_ms": int(ts_ms),
                "price": float(price),
            }
        )

    return {
        "venue": venue,
        "symbol": symbol,
        "ticks": ticks,
    }


@app.get("/api/v1/markets/first")
def first_market(timeframe: str = Query(default=DEFAULT_TIMEFRAME, min_length=1, max_length=16)) -> dict:
    payload = markets_available(timeframe=timeframe)
    markets = payload["markets"]
    if not markets:
        raise HTTPException(status_code=404, detail="No markets available")
    return markets[0]


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=False)
