import os
from pathlib import Path

import psycopg
import uvicorn
from fastapi import FastAPI, HTTPException, Query
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

    if not rows:
        return {
            "venue": venue,
            "symbol": symbol,
            "timeframe": timeframe,
            "bars": [],
        }

    bars = []
    for bucket_start, o, h, l, c, volume, trade_count in reversed(rows):
        if None in (o, h, l, c):
            continue
        bars.append(
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

    return {
        "venue": venue,
        "symbol": symbol,
        "timeframe": timeframe,
        "bars": bars,
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
