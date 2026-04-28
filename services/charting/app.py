import os
import json
import secrets
import uuid
import urllib.parse
import urllib.request
import urllib.error
import socket
import time
import threading
from pathlib import Path
from datetime import datetime, timezone, timedelta

import psycopg
import uvicorn
from fastapi import Body, FastAPI, Header, HTTPException, Path as ApiPath, Query
from fastapi.responses import PlainTextResponse
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
VALID_ASSET_CLASSES = {"fx", "crypto", "other"}
VALID_VENUES = {"oanda", "capital", "coinbase"}
ROLE_RANK = {"viewer": 0, "operator": 1, "risk_manager": 2, "admin": 3}
ROLE_DEFAULT_SECTIONS = {
    "viewer": ["overview", "ingestion", "risk", "portfolio", "execution", "charting", "ops"],
    "operator": ["overview", "ingestion", "risk", "portfolio", "execution", "charting", "ops"],
    "risk_manager": ["overview", "risk", "portfolio", "execution", "charting", "ops", "governance"],
    "admin": [
        "overview",
        "ingestion",
        "risk",
        "portfolio",
        "execution",
        "charting",
        "ops",
        "governance",
        "research",
        "config",
    ],
}

_CAPITAL_SESSION_LOCK = threading.Lock()
_CAPITAL_SESSION_HEADERS: dict[str, str] = {}
_CAPITAL_SESSION_EXPIRY: datetime | None = None
_BACKFILL_LOCKS_GUARD = threading.Lock()
_BACKFILL_LOCKS: dict[tuple[str, str], threading.Lock] = {}

app = FastAPI(title="nitra-charting")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def role_from_token(token: str | None) -> tuple[str, str]:
    if not token:
        raise HTTPException(status_code=401, detail="missing control-panel token")

    expected = {
        env("CONTROL_PANEL_VIEWER_TOKEN", "viewer-token"): "viewer",
        env("CONTROL_PANEL_OPERATOR_TOKEN", "operator-token"): "operator",
        env("CONTROL_PANEL_RISK_MANAGER_TOKEN", "risk-manager-token"): "risk_manager",
        env("CONTROL_PANEL_ADMIN_TOKEN", "admin-token"): "admin",
    }
    role = None
    for candidate, candidate_role in expected.items():
        if secrets.compare_digest(token, candidate):
            role = candidate_role
            break
    if not role:
        raise HTTPException(status_code=401, detail="invalid control-panel token")
    return role, f"{role}@local"


def require_min_role(role: str, min_role: str) -> None:
    if ROLE_RANK.get(role, -1) < ROLE_RANK.get(min_role, 99):
        raise HTTPException(status_code=403, detail=f"requires role >= {min_role}")


def get_operator_session(x_control_panel_token: str | None = Header(default=None)) -> dict:
    role, user_id = role_from_token(x_control_panel_token)
    return {
        "user_id": user_id,
        "role": role,
        "sections": ROLE_DEFAULT_SECTIONS.get(role, []),
        "issued_at": datetime.now(timezone.utc).isoformat(),
    }


def ensure_control_panel_audit_table(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS control_panel_audit_log (
              audit_id UUID PRIMARY KEY,
              user_id TEXT NOT NULL,
              role TEXT NOT NULL,
              action TEXT NOT NULL,
              section TEXT NOT NULL,
              target TEXT,
              status TEXT NOT NULL,
              reason TEXT,
              metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
              created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_control_panel_audit_log_created_at
              ON control_panel_audit_log (created_at DESC)
            """
        )


def audit_control_panel_action(
    conn: psycopg.Connection,
    *,
    user_id: str,
    role: str,
    action: str,
    section: str,
    target: str | None,
    status: str,
    reason: str | None,
    metadata: dict,
) -> None:
    ensure_control_panel_audit_table(conn)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO control_panel_audit_log (
              audit_id, user_id, role, action, section, target, status, reason, metadata
            )
            VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
            """,
            (
                str(uuid.uuid4()),
                user_id,
                role,
                action,
                section,
                target,
                status,
                reason,
                json.dumps(metadata),
            ),
        )


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/control-panel")
def control_panel(x_control_panel_token: str | None = Header(default=None)) -> FileResponse:
    get_operator_session(x_control_panel_token)
    return FileResponse(str(STATIC_DIR / "control-panel.html"))


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


def fetch_scalar(cur: psycopg.Cursor, query: str, params: tuple = ()) -> float:
    cur.execute(query, params)
    row = cur.fetchone()
    if not row or row[0] is None:
        return 0.0
    return float(row[0])


@app.get("/api/v1/control-panel/overview")
def control_panel_overview(x_control_panel_token: str | None = Header(default=None)) -> dict:
    session = get_operator_session(x_control_panel_token)
    metrics = {
        "venues_enabled": 0,
        "active_markets": 0,
        "open_gaps": 0,
        "queued_backfills": 0,
        "replay_queued": 0,
        "risk_decisions_24h": 0,
        "policy_violations_24h": 0,
        "orders_24h": 0,
        "fills_24h": 0,
        "portfolio_gross_exposure": 0.0,
        "portfolio_net_exposure": 0.0,
    }
    modules = [
        {"id": "overview", "name": "Overview", "status": "online"},
        {"id": "ingestion", "name": "Ingestion", "status": "online"},
        {"id": "risk", "name": "Risk", "status": "online"},
        {"id": "portfolio", "name": "Portfolio", "status": "online"},
        {"id": "execution", "name": "Execution", "status": "online"},
        {"id": "charting", "name": "Charting", "status": "online"},
        {"id": "ops", "name": "Ops", "status": "online"},
    ]

    try:
        with psycopg.connect(db_url()) as conn:
            with conn.cursor() as cur:
                metrics["venues_enabled"] = int(
                    fetch_scalar(
                        cur,
                        "SELECT COUNT(DISTINCT venue) FROM venue_market WHERE enabled = TRUE AND ingest_enabled = TRUE",
                    )
                )
                metrics["active_markets"] = int(
                    fetch_scalar(
                        cur,
                        "SELECT COUNT(*) FROM venue_market WHERE enabled = TRUE AND ingest_enabled = TRUE",
                    )
                )
                metrics["open_gaps"] = int(
                    fetch_scalar(cur, "SELECT COUNT(*) FROM gap_log WHERE status = 'open'")
                )
                metrics["queued_backfills"] = int(
                    fetch_scalar(cur, "SELECT COUNT(*) FROM backfill_jobs WHERE status = 'queued'")
                )
                metrics["replay_queued"] = int(
                    fetch_scalar(cur, "SELECT COUNT(*) FROM replay_audit WHERE status = 'queued'")
                )
                metrics["risk_decisions_24h"] = int(
                    fetch_scalar(
                        cur,
                        "SELECT COUNT(*) FROM risk_decision_log WHERE created_at >= now() - interval '24 hours'",
                    )
                )
                metrics["policy_violations_24h"] = int(
                    fetch_scalar(
                        cur,
                        """
                        SELECT COUNT(*)
                        FROM risk_decision_log
                        WHERE created_at >= now() - interval '24 hours'
                          AND approved = FALSE
                          AND jsonb_array_length(violations) > 0
                        """,
                    )
                )
                metrics["orders_24h"] = int(
                    fetch_scalar(
                        cur,
                        "SELECT COUNT(*) FROM execution_order_journal WHERE updated_at >= now() - interval '24 hours'",
                    )
                )
                metrics["fills_24h"] = int(
                    fetch_scalar(
                        cur,
                        "SELECT COUNT(*) FROM portfolio_fill_log WHERE created_at >= now() - interval '24 hours'",
                    )
                )
                cur.execute(
                    """
                    SELECT
                      COALESCE(gross_exposure_notional, 0),
                      COALESCE(net_exposure_notional, 0)
                    FROM portfolio_account_state
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """
                )
                row = cur.fetchone()
                if row:
                    metrics["portfolio_gross_exposure"] = float(row[0] or 0.0)
                    metrics["portfolio_net_exposure"] = float(row[1] or 0.0)
    except Exception:
        modules = [{**module, "status": "degraded"} for module in modules]

    return {
        "service": "control-panel",
        "theme": "bw-professional",
        "session": session,
        "metrics": metrics,
        "modules": modules,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/v1/control-panel/session")
def control_panel_session(x_control_panel_token: str | None = Header(default=None)) -> dict:
    return {"session": get_operator_session(x_control_panel_token)}


@app.get("/api/v1/control-panel/ingestion")
def control_panel_ingestion(
    x_control_panel_token: str | None = Header(default=None),
    status_lookback_hours: int = Query(default=24, ge=1, le=168),
    coverage_window_hours: int = Query(default=24, ge=1, le=2160),
    row_limit: int = Query(default=30, ge=1, le=200),
) -> dict:
    session = get_operator_session(x_control_panel_token)
    metrics = {
        "open_gaps": 0,
        "queued_backfills": 0,
        "failed_backfills_24h": 0,
        "replay_failed_24h": 0,
        "coverage_ratio_avg": 0.0,
        "symbols_with_open_gaps": 0,
    }
    connector_health: list[dict] = []
    backfill_recent: list[dict] = []
    replay_recent: list[dict] = []
    coverage_rows: list[dict] = []
    mode = "online"

    try:
        coverage_payload = build_coverage_status_payload(
            venue=None,
            symbol=None,
            window_hours=coverage_window_hours,
            limit=row_limit,
            status_lookback_hours=status_lookback_hours,
        )
        summary = coverage_payload.get("summary", {})
        metrics["open_gaps"] = int(summary.get("symbols_with_open_gaps", 0))
        metrics["queued_backfills"] = int(summary.get("backfill_jobs_by_status", {}).get("queued", 0))
        metrics["coverage_ratio_avg"] = float(summary.get("coverage_ratio_avg", 0.0))
        metrics["symbols_with_open_gaps"] = int(summary.get("symbols_with_open_gaps", 0))
        coverage_rows = list(coverage_payload.get("rows", []))

        with psycopg.connect(db_url()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT venue, symbol, enabled, ingest_enabled, updated_at
                    FROM venue_market
                    ORDER BY venue ASC, symbol ASC
                    LIMIT %s
                    """,
                    (row_limit,),
                )
                for venue, symbol, enabled, ingest_enabled, updated_at in cur.fetchall():
                    connector_health.append(
                        {
                            "venue": str(venue),
                            "symbol": str(symbol),
                            "enabled": bool(enabled),
                            "ingest_enabled": bool(ingest_enabled),
                            "status": "online" if enabled and ingest_enabled else "disabled",
                            "updated_at": updated_at.isoformat() if updated_at else None,
                        }
                    )

                cur.execute(
                    """
                    SELECT status, venue, canonical_symbol, requested_from, requested_to, attempt_count, updated_at
                    FROM backfill_jobs
                    ORDER BY updated_at DESC
                    LIMIT %s
                    """,
                    (row_limit,),
                )
                for status, venue, canonical_symbol, requested_from, requested_to, attempt_count, updated_at in cur.fetchall():
                    backfill_recent.append(
                        {
                            "status": str(status),
                            "venue": str(venue),
                            "symbol": str(canonical_symbol),
                            "requested_from": requested_from.isoformat() if requested_from else None,
                            "requested_to": requested_to.isoformat() if requested_to else None,
                            "attempt_count": int(attempt_count or 0),
                            "updated_at": updated_at.isoformat() if updated_at else None,
                        }
                    )

                cur.execute(
                    """
                    SELECT status, venue, canonical_symbol, started_at, completed_at
                    FROM replay_audit
                    ORDER BY started_at DESC
                    LIMIT %s
                    """,
                    (row_limit,),
                )
                for status, venue, canonical_symbol, started_at, completed_at in cur.fetchall():
                    replay_recent.append(
                        {
                            "status": str(status),
                            "venue": str(venue),
                            "symbol": str(canonical_symbol),
                            "started_at": started_at.isoformat() if started_at else None,
                            "completed_at": completed_at.isoformat() if completed_at else None,
                        }
                    )

                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM backfill_jobs
                    WHERE status LIKE 'failed%%'
                      AND updated_at >= now() - interval '24 hours'
                    """
                )
                metrics["failed_backfills_24h"] = int(cur.fetchone()[0] or 0)

                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM replay_audit
                    WHERE status LIKE 'failed%%'
                      AND started_at >= now() - interval '24 hours'
                    """
                )
                metrics["replay_failed_24h"] = int(cur.fetchone()[0] or 0)
    except Exception:
        mode = "degraded"

    return {
        "service": "control-panel",
        "module": "ingestion",
        "mode": mode,
        "session": session,
        "metrics": metrics,
        "connector_health": connector_health,
        "coverage_rows": coverage_rows,
        "backfill_recent": backfill_recent,
        "replay_recent": replay_recent,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/v1/control-panel/ingestion/backfill-window")
def control_panel_ingestion_backfill_window(
    payload: dict = Body(...),
    x_control_panel_token: str | None = Header(default=None),
) -> dict:
    session = get_operator_session(x_control_panel_token)
    require_min_role(session["role"], "operator")

    venue = str(payload.get("venue", "")).strip().lower()
    symbol = str(payload.get("symbol", "")).strip().upper()
    from_ts = str(payload.get("from_ts", "")).strip()
    to_ts = str(payload.get("to_ts", "")).strip()
    justification = str(payload.get("justification", "")).strip()
    if len(justification) < 12:
        raise HTTPException(status_code=400, detail="justification must be at least 12 characters")
    if not venue or not symbol:
        raise HTTPException(status_code=400, detail="venue and symbol are required")

    start_dt = parse_window_ts(from_ts)
    end_dt = parse_window_ts(to_ts)
    if end_dt < start_dt:
        raise HTTPException(status_code=400, detail="invalid window")
    if (end_dt - start_dt) > timedelta(days=7):
        raise HTTPException(status_code=400, detail="window exceeds 7 days safety cap")

    result = run_backfill_window(
        venue=venue,
        symbol=symbol,
        start_dt=start_dt,
        end_dt=end_dt,
        trigger="control_panel_window",
        wait_for_lock=True,
        max_ranges=200,
    )
    try:
        with psycopg.connect(db_url()) as conn:
            audit_control_panel_action(
                conn,
                user_id=session["user_id"],
                role=session["role"],
                action="ingestion.backfill_window",
                section="ingestion",
                target=f"{venue}:{symbol}",
                status="approved",
                reason=None,
                metadata={
                    "from_ts": from_ts,
                    "to_ts": to_ts,
                    "justification": justification,
                    "result_status": result.get("status"),
                },
            )
            conn.commit()
    except Exception:
        pass

    return {"status": "accepted", "session": session, "result": result}


@app.post("/api/v1/control-panel/actions/privileged")
def control_panel_privileged_action(
    payload: dict = Body(...),
    x_control_panel_token: str | None = Header(default=None),
) -> dict:
    session = get_operator_session(x_control_panel_token)
    action = str(payload.get("action", "")).strip()
    section = str(payload.get("section", "")).strip() or "general"
    target = payload.get("target")
    justification = str(payload.get("justification", "")).strip()
    min_role = str(payload.get("min_role", "admin")).strip() or "admin"

    if min_role not in ROLE_RANK:
        raise HTTPException(status_code=400, detail="invalid min_role")
    if not action:
        raise HTTPException(status_code=400, detail="action is required")
    if len(justification) < 12:
        raise HTTPException(status_code=400, detail="justification must be at least 12 characters")

    status = "approved"
    reason = None
    try:
        require_min_role(session["role"], min_role)
    except HTTPException:
        status = "denied"
        reason = f"insufficient_role:{session['role']}"

    try:
        with psycopg.connect(db_url()) as conn:
            audit_control_panel_action(
                conn,
                user_id=session["user_id"],
                role=session["role"],
                action=action,
                section=section,
                target=str(target) if target is not None else None,
                status=status,
                reason=reason,
                metadata={
                    "justification": justification,
                    "min_role": min_role,
                },
            )
            conn.commit()
    except Exception:
        pass

    if status == "denied":
        raise HTTPException(status_code=403, detail=f"action denied: {reason}")

    return {
        "status": status,
        "action": action,
        "section": section,
        "target": target,
        "approved_by": session["user_id"],
        "approved_at": datetime.now(timezone.utc).isoformat(),
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


def timeframe_minutes(timeframe: str) -> int:
    tf = timeframe.strip().lower()
    if tf.endswith("m") and tf[:-1].isdigit():
        return max(1, int(tf[:-1]))
    if tf.endswith("h") and tf[:-1].isdigit():
        return max(1, int(tf[:-1]) * 60)
    if tf.endswith("d") and tf[:-1].isdigit():
        return max(1, int(tf[:-1]) * 1440)
    return 1


def timeframe_bucket_start(ts: datetime, tf_minutes: int) -> datetime:
    minute_ts = int(ts.astimezone(timezone.utc).replace(second=0, microsecond=0).timestamp())
    bucket_seconds = max(60, tf_minutes * 60)
    bucket = (minute_ts // bucket_seconds) * bucket_seconds
    return datetime.fromtimestamp(bucket, tz=timezone.utc)


def aggregate_1m_rows(rows: list[tuple], tf_minutes: int) -> list[tuple]:
    if tf_minutes <= 1:
        return rows
    out: list[tuple] = []
    current: dict | None = None
    for bucket_start, open_, high, low, close, volume, trade_count in rows:
        if None in (bucket_start, open_, high, low, close):
            continue
        slot = timeframe_bucket_start(bucket_start, tf_minutes)
        if current is None or current["bucket_start"] != slot:
            if current is not None:
                out.append(
                    (
                        current["bucket_start"],
                        current["open"],
                        current["high"],
                        current["low"],
                        current["close"],
                        current["volume"],
                        current["trade_count"],
                    )
                )
            current = {
                "bucket_start": slot,
                "open": float(open_),
                "high": float(high),
                "low": float(low),
                "close": float(close),
                "volume": float(volume or 0.0),
                "trade_count": int(trade_count or 0),
            }
            continue
        current["high"] = max(current["high"], float(high))
        current["low"] = min(current["low"], float(low))
        current["close"] = float(close)
        current["volume"] += float(volume or 0.0)
        current["trade_count"] += int(trade_count or 0)
    if current is not None:
        out.append(
            (
                current["bucket_start"],
                current["open"],
                current["high"],
                current["low"],
                current["close"],
                current["volume"],
                current["trade_count"],
            )
        )
    return out


def get_backfill_lock(venue: str, symbol: str) -> threading.Lock:
    key = (venue.lower(), symbol.upper())
    with _BACKFILL_LOCKS_GUARD:
        existing = _BACKFILL_LOCKS.get(key)
        if existing is not None:
            return existing
        lock = threading.Lock()
        _BACKFILL_LOCKS[key] = lock
        return lock


def is_crypto_symbol(symbol: str) -> bool:
    upper = symbol.upper()
    if len(upper) >= 6 and upper.endswith("USD"):
        return upper[:-3] in CRYPTO_BASES
    if len(upper) >= 7 and upper.endswith("USDT"):
        return upper[:-4] in CRYPTO_BASES
    if len(upper) >= 7 and upper.endswith("USDC"):
        return upper[:-4] in CRYPTO_BASES
    return False


def normalize_venue(venue: str) -> str:
    norm = venue.strip().lower()
    if not norm:
        raise HTTPException(status_code=400, detail="venue is required")
    return norm


def normalize_symbol(symbol: str) -> str:
    norm = "".join(ch for ch in symbol.strip().upper() if ch.isalnum())
    if not norm:
        raise HTTPException(status_code=400, detail="symbol is required")
    return norm


def infer_asset_class(symbol: str, fallback: str | None = None) -> str:
    normalized_fallback = (fallback or "").strip().lower()
    if normalized_fallback in VALID_ASSET_CLASSES:
        return normalized_fallback
    return "crypto" if is_crypto_symbol(symbol) else "fx"


def ensure_venue_market_schema(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS venue_market (
              venue TEXT NOT NULL,
              symbol TEXT NOT NULL,
              asset_class TEXT NOT NULL DEFAULT 'fx',
              enabled BOOLEAN NOT NULL DEFAULT TRUE,
              ingest_enabled BOOLEAN NOT NULL DEFAULT TRUE,
              metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
              created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
              updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
              PRIMARY KEY (venue, symbol),
              CHECK (asset_class IN ('fx', 'crypto', 'other'))
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_venue_market_enabled
              ON venue_market (enabled, ingest_enabled, venue, symbol)
            """
        )


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


def parse_float(raw: object) -> float | None:
    if isinstance(raw, (float, int)):
        return float(raw)
    if isinstance(raw, str):
        try:
            return float(raw)
        except ValueError:
            return None
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
        retries = 0
        while True:
            try:
                with urllib.request.urlopen(req, timeout=VENUE_FETCH_TIMEOUT_SECS) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as exc:
                if exc.code in {401, 403}:
                    # Session may have expired; retry once with forced session refresh.
                    headers = capital_session_headers(force_refresh=True)
                    req = urllib.request.Request(url, headers=headers, method="GET")
                    retries += 1
                    if retries <= 1:
                        continue
                elif exc.code in {429, 500, 503} and retries < 2:
                    retries += 1
                    time.sleep(0.8 * retries)
                    continue
                elif exc.code == 404:
                    payload = {"prices": []}
                    break
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
            low = parse_float(row[1])
            high = parse_float(row[2])
            open_ = parse_float(row[3])
            close = parse_float(row[4])
            if None in (open_, high, low, close):
                continue
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
        open_ = parse_float(open_raw)
        high = parse_float(high_raw)
        low = parse_float(low_raw)
        close = parse_float(close_raw)
        if None in (open_, high, low, close):
            continue
        bars.append((ts, open_, high, low, close, 0, ts))
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
    # Process newest ranges first so recent chart continuity is restored before older history.
    for start_dt, end_dt in reversed(ranges):
        chunks = chunk_range(start_dt, end_dt, chunk_minutes=chunk_minutes)
        for chunk_start, chunk_end in reversed(chunks):
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


@app.post("/api/v1/backfill/adapter-check")
def adapter_check(
    venue: str = Body(min_length=1, max_length=64),
    symbol: str = Body(min_length=1, max_length=64),
) -> dict:
    venue_norm = venue.strip().lower()
    symbol_norm = symbol.strip().upper()
    end_dt = datetime.now(timezone.utc).replace(second=0, microsecond=0) - timedelta(minutes=1)
    start_dt = end_dt - timedelta(minutes=30)
    try:
        if venue_norm == "oanda":
            bars = fetch_oanda_range(symbol_norm, start_dt, end_dt)
        elif venue_norm == "coinbase":
            bars = fetch_coinbase_range(symbol_norm, start_dt, end_dt)
        elif venue_norm == "capital":
            bars = fetch_capital_range(symbol_norm, start_dt, end_dt)
        else:
            raise HTTPException(status_code=400, detail=f"adapter not implemented for venue={venue_norm}")
    except Exception as exc:
        return {
            "venue": venue_norm,
            "symbol": symbol_norm,
            "status": "error",
            "error": str(exc),
            "window": {"start": start_dt.isoformat(), "end": end_dt.isoformat()},
            "rows": 0,
        }

    return {
        "venue": venue_norm,
        "symbol": symbol_norm,
        "status": "ok" if bars else "empty",
        "window": {"start": start_dt.isoformat(), "end": end_dt.isoformat()},
        "rows": len(bars),
        "first_bar": bars[0][0].isoformat() if bars else None,
        "last_bar": bars[-1][0].isoformat() if bars else None,
    }


@app.post("/api/v1/backfill/90d")
def backfill_90d(
    venue: str = Body(min_length=1, max_length=64),
    symbol: str = Body(min_length=1, max_length=64),
) -> dict:
    start_dt, end_dt = canonical_window_90d()
    return run_backfill_window(
        venue=venue.strip().lower(),
        symbol=symbol.strip().upper(),
        start_dt=start_dt,
        end_dt=end_dt,
        trigger="manual_90d",
        wait_for_lock=True,
    )


def run_backfill_window(
    *,
    venue: str,
    symbol: str,
    start_dt: datetime,
    end_dt: datetime,
    trigger: str,
    wait_for_lock: bool,
    max_ranges: int | None = None,
) -> dict:
    venue_norm = venue.strip().lower()
    symbol_norm = symbol.strip().upper()
    weekday_only = fx_weekday_only_policy(venue_norm, symbol_norm)
    broker_symbols = broker_symbol_candidates(venue_norm, symbol_norm)
    requested_minutes = expected_minutes(start_dt, end_dt, weekday_only=weekday_only)
    first_missing_after: list[str] = []
    missing_ranges: list[tuple[datetime, datetime]] = []
    upserted_from_ticks = 0
    source_tick_count = 0
    min_ts = None
    max_ts = None
    missing_before_count = 0

    lock = get_backfill_lock(venue_norm, symbol_norm)
    locked = lock.acquire(blocking=wait_for_lock)
    if not locked:
        return {
            "venue": venue_norm,
            "symbol": symbol_norm,
            "requested_window": {"start": start_dt.isoformat(), "end": end_dt.isoformat()},
            "requested_minutes": requested_minutes,
            "complete_90d_1m": False,
            "continuity_policy": "weekday_only_for_fx" if weekday_only else "all_minutes",
            "trigger": trigger,
            "status": "skipped_lock_busy",
            "venue_fetch_error": "backfill already running for symbol",
        }

    try:
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

        if max_ranges is not None and len(missing_ranges) > max_ranges:
            missing_ranges = missing_ranges[-max_ranges:]

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
            "missing_range_count": len(missing_ranges),
            "missing_after_fetch_count": len(missing_after),
            "coverage_ratio": (covered_minutes / requested_minutes) if requested_minutes > 0 else 0.0,
            "complete_90d_1m": complete,
            "continuity_policy": "weekday_only_for_fx" if weekday_only else "all_minutes",
            "first_missing_minutes": first_missing_after if not complete else [],
            "venue_fetch_error": venue_fetch_error,
            "trigger": trigger,
            "range_priority": "recent_to_old",
            "status": "ok",
            "note": "Strict coverage mode: backfill rebuilds from raw_tick, then fetches missing required 1m windows from venue adapters. For FX venues, closed-market weekend minutes are excluded from required continuity.",
        }
    finally:
        lock.release()


def parse_window_ts(raw: str) -> datetime:
    ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc).replace(second=0, microsecond=0)


@app.post("/api/v1/backfill/window")
def backfill_window(
    venue: str = Body(min_length=1, max_length=64),
    symbol: str = Body(min_length=1, max_length=64),
    from_ts: str = Body(min_length=1, max_length=64),
    to_ts: str = Body(min_length=1, max_length=64),
) -> dict:
    start_dt = parse_window_ts(from_ts)
    end_dt = parse_window_ts(to_ts)
    if end_dt < start_dt:
        raise HTTPException(status_code=400, detail="invalid window: to_ts is before from_ts")
    return run_backfill_window(
        venue=venue.strip().lower(),
        symbol=symbol.strip().upper(),
        start_dt=start_dt,
        end_dt=end_dt,
        trigger="manual_window",
        wait_for_lock=True,
    )


def fetch_grouped_status_counts(
    conn: psycopg.Connection,
    table: str,
    time_column: str,
    lookback_hours: int,
) -> dict[str, int]:
    query = f"""
    SELECT status, COUNT(*)::bigint
    FROM {table}
    WHERE {time_column} >= now() - (%s::int * interval '1 hour')
    GROUP BY status
    """
    out: dict[str, int] = {}
    with conn.cursor() as cur:
        cur.execute(query, (lookback_hours,))
        for status, count in cur.fetchall():
            out[str(status)] = int(count)
    return out


def build_coverage_status_payload(
    *,
    venue: str | None,
    symbol: str | None,
    window_hours: int,
    limit: int,
    status_lookback_hours: int,
) -> dict:
    end_dt = datetime.now(timezone.utc).replace(second=0, microsecond=0) - timedelta(minutes=1)
    start_dt = end_dt - timedelta(hours=max(1, window_hours))

    where_parts = ["cs.timeframe = '1m'"]
    params: list[object] = [start_dt, end_dt, start_dt, end_dt]
    if venue:
        where_parts.append("cs.venue = %s")
        params.append(venue.strip().lower())
    if symbol:
        where_parts.append("cs.canonical_symbol = %s")
        params.append(symbol.strip().upper())
    params.append(max(1, min(limit, 1000)))
    where_clause = " AND ".join(where_parts)

    query = f"""
    SELECT
      cs.venue,
      cs.canonical_symbol,
      cs.last_bucket_start,
      cs.last_seen_at,
      COALESCE(b.actual_minutes, 0)::bigint AS actual_minutes,
      COALESCE(g.open_gap_count, 0)::bigint AS open_gap_count,
      g.oldest_gap_start,
      g.newest_gap_end
    FROM coverage_state cs
    LEFT JOIN LATERAL (
      SELECT COUNT(*)::bigint AS actual_minutes
      FROM ohlcv_bar ob
      WHERE ob.venue = cs.venue
        AND ob.canonical_symbol = cs.canonical_symbol
        AND ob.timeframe = '1m'
        AND ob.bucket_start >= %s
        AND ob.bucket_start <= %s
    ) b ON TRUE
    LEFT JOIN LATERAL (
      SELECT
        COUNT(*)::bigint AS open_gap_count,
        MIN(gap_start) AS oldest_gap_start,
        MAX(gap_end) AS newest_gap_end
      FROM gap_log gl
      WHERE gl.venue = cs.venue
        AND gl.canonical_symbol = cs.canonical_symbol
        AND gl.timeframe = '1m'
        AND gl.status IN ('open', 'backfill_queued')
        AND gl.gap_end >= %s
        AND gl.gap_start <= %s
    ) g ON TRUE
    WHERE {where_clause}
    ORDER BY cs.last_seen_at DESC
    LIMIT %s
    """

    rows_payload: list[dict] = []
    with psycopg.connect(db_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

        backfill_jobs = fetch_grouped_status_counts(conn, "backfill_jobs", "updated_at", status_lookback_hours)
        replay_audit = fetch_grouped_status_counts(conn, "replay_audit", "started_at", status_lookback_hours)

    symbols_with_open_gaps = 0
    coverage_ratio_sum = 0.0
    for row in rows:
        row_venue = str(row[0]).lower()
        row_symbol = str(row[1]).upper()
        last_bucket_start = row[2]
        last_seen_at = row[3]
        actual_minutes = int(row[4] or 0)
        open_gap_count = int(row[5] or 0)
        oldest_gap_start = row[6]
        newest_gap_end = row[7]
        if open_gap_count > 0:
            symbols_with_open_gaps += 1

        expected = expected_minutes(
            start_dt,
            end_dt,
            weekday_only=fx_weekday_only_policy(row_venue, row_symbol),
        )
        ratio = 1.0 if expected <= 0 else min(1.0, actual_minutes / expected)
        coverage_ratio_sum += ratio
        rows_payload.append(
            {
                "venue": row_venue,
                "symbol": row_symbol,
                "last_bucket_start": last_bucket_start.isoformat() if last_bucket_start else None,
                "last_seen_at": last_seen_at.isoformat() if last_seen_at else None,
                "actual_minutes": actual_minutes,
                "expected_minutes": expected,
                "coverage_ratio": ratio,
                "open_gap_count": open_gap_count,
                "oldest_open_gap_start": oldest_gap_start.isoformat() if oldest_gap_start else None,
                "newest_open_gap_end": newest_gap_end.isoformat() if newest_gap_end else None,
            }
        )

    total_symbols = len(rows_payload)
    avg_ratio = (coverage_ratio_sum / total_symbols) if total_symbols else 0.0
    return {
        "window": {"start": start_dt.isoformat(), "end": end_dt.isoformat(), "hours": window_hours},
        "filters": {"venue": venue, "symbol": symbol, "limit": limit},
        "summary": {
            "symbols_total": total_symbols,
            "symbols_with_open_gaps": symbols_with_open_gaps,
            "coverage_ratio_avg": avg_ratio,
            "backfill_jobs_by_status": backfill_jobs,
            "replay_audit_by_status": replay_audit,
            "status_lookback_hours": status_lookback_hours,
        },
        "rows": rows_payload,
    }


@app.get("/api/v1/coverage/status")
def coverage_status(
    venue: str | None = Query(default=None, min_length=1, max_length=64),
    symbol: str | None = Query(default=None, min_length=1, max_length=64),
    window_hours: int = Query(default=24 * 90, ge=1, le=24 * 180),
    limit: int = Query(default=200, ge=1, le=1000),
    status_lookback_hours: int = Query(default=24, ge=1, le=24 * 30),
) -> dict:
    return build_coverage_status_payload(
        venue=venue,
        symbol=symbol,
        window_hours=window_hours,
        limit=limit,
        status_lookback_hours=status_lookback_hours,
    )


@app.get("/api/v1/coverage/metrics", response_class=PlainTextResponse)
def coverage_metrics(
    window_hours: int = Query(default=24 * 90, ge=1, le=24 * 180),
    limit: int = Query(default=500, ge=1, le=1000),
    status_lookback_hours: int = Query(default=24, ge=1, le=24 * 30),
) -> PlainTextResponse:
    payload = build_coverage_status_payload(
        venue=None,
        symbol=None,
        window_hours=window_hours,
        limit=limit,
        status_lookback_hours=status_lookback_hours,
    )
    summary = payload["summary"]
    lines = [
        "# HELP nitra_coverage_symbols_total Number of tracked symbols in coverage snapshot",
        "# TYPE nitra_coverage_symbols_total gauge",
        f"nitra_coverage_symbols_total {summary['symbols_total']}",
        "# HELP nitra_coverage_symbols_with_open_gaps Number of symbols currently containing open/backfill_queued gaps",
        "# TYPE nitra_coverage_symbols_with_open_gaps gauge",
        f"nitra_coverage_symbols_with_open_gaps {summary['symbols_with_open_gaps']}",
        "# HELP nitra_coverage_ratio_avg Average 90d coverage ratio across symbols",
        "# TYPE nitra_coverage_ratio_avg gauge",
        f"nitra_coverage_ratio_avg {summary['coverage_ratio_avg']:.6f}",
    ]
    for status, count in sorted(summary["backfill_jobs_by_status"].items()):
        lines.append(f'nitra_backfill_jobs_total{{status="{status}"}} {count}')
    for status, count in sorted(summary["replay_audit_by_status"].items()):
        lines.append(f'nitra_replay_audit_total{{status="{status}"}} {count}')
    return PlainTextResponse("\n".join(lines) + "\n")


@app.get("/api/v1/venues")
def venues() -> dict:
    query = """
    SELECT DISTINCT venue
    FROM venue_market
    WHERE enabled = TRUE
    ORDER BY venue
    """
    with psycopg.connect(db_url()) as conn:
        ensure_venue_market_schema(conn)
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
    values = {str(row[0]).lower() for row in rows}
    values.update(VALID_VENUES)
    return {"venues": sorted(values)}


@app.post("/api/v1/venues")
def create_venue(
    venue: str = Body(min_length=2, max_length=64),
) -> dict:
    venue_norm = normalize_venue(venue)
    if venue_norm not in VALID_VENUES:
        raise HTTPException(status_code=400, detail=f"unsupported venue '{venue_norm}'")
    return {"status": "ok", "venue": venue_norm}


@app.get("/api/v1/venues/{venue}/markets")
def venue_markets(
    venue: str = ApiPath(min_length=1, max_length=64),
) -> dict:
    venue_norm = normalize_venue(venue)
    query = """
    WITH bars AS (
      SELECT
        venue,
        canonical_symbol AS symbol,
        MAX(bucket_start) AS last_bar_ts,
        COUNT(*)::bigint AS bar_count
      FROM ohlcv_bar
      WHERE timeframe = '1m'
      GROUP BY venue, canonical_symbol
    )
    SELECT
      vm.venue,
      vm.symbol,
      vm.asset_class,
      vm.enabled,
      vm.ingest_enabled,
      COALESCE(b.last_bar_ts, NULL) AS last_bar_ts,
      COALESCE(b.bar_count, 0)::bigint AS bar_count
    FROM venue_market vm
    LEFT JOIN bars b
      ON b.venue = vm.venue AND b.symbol = vm.symbol
    WHERE vm.venue = %s
    ORDER BY vm.symbol
    """
    with psycopg.connect(db_url()) as conn:
        ensure_venue_market_schema(conn)
        with conn.cursor() as cur:
            cur.execute(query, (venue_norm,))
            rows = cur.fetchall()
    markets = []
    for row in rows:
        markets.append(
            {
                "venue": str(row[0]).lower(),
                "symbol": str(row[1]).upper(),
                "asset_class": str(row[2]).lower(),
                "enabled": bool(row[3]),
                "ingest_enabled": bool(row[4]),
                "last_bar_ts": row[5].isoformat() if row[5] else None,
                "bar_count": int(row[6] or 0),
            }
        )
    return {"venue": venue_norm, "markets": markets}


@app.post("/api/v1/venues/{venue}/markets")
def create_venue_market(
    venue: str = ApiPath(min_length=1, max_length=64),
    symbol: str = Body(min_length=1, max_length=64),
    asset_class: str | None = Body(default=None),
    enabled: bool = Body(default=True),
    ingest_enabled: bool = Body(default=True),
) -> dict:
    venue_norm = normalize_venue(venue)
    if venue_norm not in VALID_VENUES:
        raise HTTPException(status_code=400, detail=f"unsupported venue '{venue_norm}'")
    symbol_norm = normalize_symbol(symbol)
    asset_class_norm = infer_asset_class(symbol_norm, asset_class)

    with psycopg.connect(db_url()) as conn:
        ensure_venue_market_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO venue_market (venue, symbol, asset_class, enabled, ingest_enabled)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (venue, symbol)
                DO UPDATE SET
                  asset_class = EXCLUDED.asset_class,
                  enabled = EXCLUDED.enabled,
                  ingest_enabled = EXCLUDED.ingest_enabled,
                  updated_at = now()
                """,
                (venue_norm, symbol_norm, asset_class_norm, enabled, ingest_enabled),
            )
        conn.commit()
    return {
        "status": "ok",
        "market": {
            "venue": venue_norm,
            "symbol": symbol_norm,
            "asset_class": asset_class_norm,
            "enabled": enabled,
            "ingest_enabled": ingest_enabled,
        },
    }


@app.post("/api/v1/ingestion/start")
def start_ingestion(
    venue: str = Body(min_length=1, max_length=64),
    symbol: str = Body(min_length=1, max_length=64),
) -> dict:
    venue_norm = normalize_venue(venue)
    symbol_norm = normalize_symbol(symbol)
    with psycopg.connect(db_url()) as conn:
        ensure_venue_market_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO venue_market (venue, symbol, asset_class, enabled, ingest_enabled)
                VALUES (%s, %s, %s, TRUE, TRUE)
                ON CONFLICT (venue, symbol)
                DO UPDATE SET
                  enabled = TRUE,
                  ingest_enabled = TRUE,
                  updated_at = now()
                """,
                (venue_norm, symbol_norm, infer_asset_class(symbol_norm, None)),
            )
        conn.commit()
    return {"status": "ok", "venue": venue_norm, "symbol": symbol_norm, "ingest_enabled": True}


@app.get("/api/v1/markets/available")
def markets_available(timeframe: str = Query(default=DEFAULT_TIMEFRAME, min_length=1, max_length=16)) -> dict:
    tf = timeframe.strip().lower()
    tf_minutes = timeframe_minutes(tf)
    query = """
    WITH bars AS (
      SELECT
        venue,
        canonical_symbol AS symbol,
        MAX(bucket_start) AS last_bar_ts,
        COUNT(*)::bigint AS bar_count
      FROM ohlcv_bar
      WHERE timeframe = '1m'
      GROUP BY venue, canonical_symbol
    ),
    cfg AS (
      SELECT
        venue,
        symbol,
        asset_class,
        ingest_enabled
      FROM venue_market
      WHERE enabled = TRUE
    )
    SELECT
      COALESCE(cfg.venue, bars.venue) AS venue,
      COALESCE(cfg.symbol, bars.symbol) AS symbol,
      bars.last_bar_ts,
      COALESCE(bars.bar_count, 0)::bigint AS bar_count,
      COALESCE(cfg.ingest_enabled, FALSE) AS ingest_enabled,
      COALESCE(cfg.asset_class, 'other') AS asset_class
    FROM cfg
    FULL OUTER JOIN bars
      ON bars.venue = cfg.venue
     AND bars.symbol = cfg.symbol
    ORDER BY venue, symbol
    """
    with psycopg.connect(db_url()) as conn:
        ensure_venue_market_schema(conn)
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()

    markets = []
    for venue, symbol, last_bar_ts, bar_count, ingest_enabled, asset_class in rows:
        if tf_minutes <= 1:
            derived_count = int(bar_count)
            derived_ts = last_bar_ts
        else:
            raw_count = int(bar_count)
            derived_count = 0 if raw_count <= 0 else max(1, (raw_count + tf_minutes - 1) // tf_minutes)
            derived_ts = timeframe_bucket_start(last_bar_ts, tf_minutes) if last_bar_ts else None
        markets.append(
            {
                "venue": venue,
                "symbol": symbol,
                "timeframe": tf,
                "last_bar_ts": derived_ts.isoformat() if derived_ts else None,
                "bar_count": derived_count,
                "ingest_enabled": bool(ingest_enabled),
                "asset_class": str(asset_class),
            }
        )

    return {"timeframe": tf, "markets": markets}


@app.get("/api/v1/bars/hot")
def bars_hot(
    venue: str = Query(min_length=1, max_length=64),
    symbol: str = Query(min_length=1, max_length=64),
    timeframe: str = Query(default=DEFAULT_TIMEFRAME, min_length=1, max_length=16),
    limit: int = Query(default=DEFAULT_LIMIT, ge=10, le=3000),
) -> dict:
    tf = timeframe.strip().lower()
    tf_minutes = timeframe_minutes(tf)
    base_query = """
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

    rows: list[tuple]
    with psycopg.connect(db_url()) as conn:
        with conn.cursor() as cur:
            if tf_minutes <= 1:
                cur.execute(base_query, (venue, symbol, "1m", limit))
                rows = cur.fetchall()
            else:
                raw_limit = min(200_000, (limit * tf_minutes) + (tf_minutes * 2))
                cur.execute(base_query, (venue, symbol, "1m", raw_limit))
                raw_rows_desc = cur.fetchall()
                raw_rows_asc = list(reversed(raw_rows_desc))
                rows = list(reversed(aggregate_1m_rows(raw_rows_asc, tf_minutes)[-limit:]))

    bars = _rows_to_bars(rows)

    return {
        "venue": venue,
        "symbol": symbol,
        "timeframe": tf,
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
    tf = timeframe.strip().lower()
    tf_minutes = timeframe_minutes(tf)
    base_query = """
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

    rows: list[tuple]
    has_more: bool
    with psycopg.connect(db_url()) as conn:
        with conn.cursor() as cur:
            if tf_minutes <= 1:
                cur.execute(base_query, (venue, symbol, "1m", before_dt, limit + 1))
                rows = cur.fetchall()
                has_more = len(rows) > limit
                rows = rows[:limit]
            else:
                raw_limit = min(200_000, ((limit + 1) * tf_minutes) + (tf_minutes * 2))
                cur.execute(base_query, (venue, symbol, "1m", before_dt, raw_limit))
                raw_rows_desc = cur.fetchall()
                raw_rows_asc = list(reversed(raw_rows_desc))
                aggregated = aggregate_1m_rows(raw_rows_asc, tf_minutes)
                has_more = len(aggregated) > limit
                selected = aggregated[-limit:]
                rows = list(reversed(selected))

    bars = _rows_to_bars(rows)
    return {
        "venue": venue,
        "symbol": symbol,
        "timeframe": tf,
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
