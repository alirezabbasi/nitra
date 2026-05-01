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
from fastapi.responses import PlainTextResponse, Response
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
    "viewer": ["overview", "ingestion", "kpi", "risk", "portfolio", "execution", "charting", "ops"],
    "operator": ["overview", "ingestion", "kpi", "risk", "portfolio", "execution", "charting", "ops"],
    "risk_manager": ["overview", "kpi", "risk", "portfolio", "execution", "charting", "ops", "governance"],
    "admin": [
        "overview",
        "ingestion",
        "kpi",
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
def control_panel(
    x_control_panel_token: str | None = Header(default=None),
    token: str | None = Query(default=None),
) -> FileResponse:
    # Browser-friendly fallback: allow token via query for the HTML page load only.
    get_operator_session(x_control_panel_token or token)
    return FileResponse(str(STATIC_DIR / "control-panel.html"))


@app.get("/favicon.ico")
def favicon() -> Response:
    return Response(status_code=204)


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
    failover_policies: list[dict] = []
    session_policies: list[dict] = []
    ws_policies: list[dict] = []
    failover_runtime: dict = {
        "configured_enabled_venues": 0,
        "configured_disabled_venues": 0,
        "active_market_venues": [],
        "degraded_market_venues": [],
        "updated_at": None,
    }
    session_runtime: dict = {
        "configured_enabled_venues": 0,
        "configured_disabled_venues": 0,
        "capital_session_cached": False,
        "capital_session_expires_in_seconds": None,
        "updated_at": None,
    }
    ws_runtime: dict = {
        "configured_enabled_venues": 0,
        "configured_disabled_venues": 0,
        "active_markets": 0,
        "updated_at": None,
    }
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
            ensure_ingestion_failover_seed_data(conn)
            ensure_ingestion_session_seed_data(conn)
            ensure_ingestion_ws_seed_data(conn)
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
                    SELECT
                      venue,
                      enabled,
                      primary_endpoint,
                      secondary_endpoints,
                      failure_threshold,
                      cooldown_seconds,
                      reconnect_backoff_seconds,
                      max_backoff_seconds,
                      request_timeout_seconds,
                      jitter_pct,
                      updated_by,
                      updated_at
                    FROM control_panel_ingestion_failover_policy
                    ORDER BY venue ASC
                    """
                )
                for (
                    venue,
                    enabled,
                    primary_endpoint,
                    secondary_endpoints,
                    failure_threshold,
                    cooldown_seconds,
                    reconnect_backoff_seconds,
                    max_backoff_seconds,
                    request_timeout_seconds,
                    jitter_pct,
                    updated_by,
                    updated_at,
                ) in cur.fetchall():
                    failover_policies.append(
                        {
                            "venue": str(venue),
                            "enabled": bool(enabled),
                            "primary_endpoint": str(primary_endpoint),
                            "secondary_endpoints": secondary_endpoints if isinstance(secondary_endpoints, list) else [],
                            "failure_threshold": int(failure_threshold or 0),
                            "cooldown_seconds": int(cooldown_seconds or 0),
                            "reconnect_backoff_seconds": int(reconnect_backoff_seconds or 0),
                            "max_backoff_seconds": int(max_backoff_seconds or 0),
                            "request_timeout_seconds": int(request_timeout_seconds or 0),
                            "jitter_pct": float(jitter_pct or 0.0),
                            "updated_by": str(updated_by),
                            "updated_at": updated_at.isoformat() if updated_at else None,
                        }
                    )
                failover_runtime = ingestion_failover_runtime(conn)
                session_runtime = ingestion_session_runtime(conn)
                ws_runtime = ingestion_ws_runtime(conn)
                cur.execute(
                    """
                    SELECT
                      venue,
                      enabled,
                      auth_mode,
                      token_ttl_seconds,
                      refresh_lead_seconds,
                      max_refresh_retries,
                      lockout_cooldown_seconds,
                      classify_401,
                      classify_403,
                      classify_429,
                      classify_5xx,
                      updated_by,
                      updated_at
                    FROM control_panel_ingestion_session_policy
                    ORDER BY venue ASC
                    """
                )
                for (
                    venue,
                    enabled,
                    auth_mode,
                    token_ttl_seconds,
                    refresh_lead_seconds,
                    max_refresh_retries,
                    lockout_cooldown_seconds,
                    classify_401,
                    classify_403,
                    classify_429,
                    classify_5xx,
                    updated_by,
                    updated_at,
                ) in cur.fetchall():
                    session_policies.append(
                        {
                            "venue": str(venue),
                            "enabled": bool(enabled),
                            "auth_mode": str(auth_mode),
                            "token_ttl_seconds": int(token_ttl_seconds or 0),
                            "refresh_lead_seconds": int(refresh_lead_seconds or 0),
                            "max_refresh_retries": int(max_refresh_retries or 0),
                            "lockout_cooldown_seconds": int(lockout_cooldown_seconds or 0),
                            "classify_401": str(classify_401),
                            "classify_403": str(classify_403),
                            "classify_429": str(classify_429),
                            "classify_5xx": str(classify_5xx),
                            "updated_by": str(updated_by),
                            "updated_at": updated_at.isoformat() if updated_at else None,
                        }
                    )
                cur.execute(
                    """
                    SELECT
                      venue,
                      enabled,
                      heartbeat_interval_seconds,
                      stale_after_seconds,
                      reconnect_backoff_seconds,
                      max_backoff_seconds,
                      jitter_pct,
                      max_consecutive_failures,
                      updated_by,
                      updated_at
                    FROM control_panel_ingestion_ws_policy
                    ORDER BY venue ASC
                    """
                )
                for (
                    venue,
                    enabled,
                    heartbeat_interval_seconds,
                    stale_after_seconds,
                    reconnect_backoff_seconds,
                    max_backoff_seconds,
                    jitter_pct,
                    max_consecutive_failures,
                    updated_by,
                    updated_at,
                ) in cur.fetchall():
                    ws_policies.append(
                        {
                            "venue": str(venue),
                            "enabled": bool(enabled),
                            "heartbeat_interval_seconds": int(heartbeat_interval_seconds or 0),
                            "stale_after_seconds": int(stale_after_seconds or 0),
                            "reconnect_backoff_seconds": int(reconnect_backoff_seconds or 0),
                            "max_backoff_seconds": int(max_backoff_seconds or 0),
                            "jitter_pct": float(jitter_pct or 0.0),
                            "max_consecutive_failures": int(max_consecutive_failures or 0),
                            "updated_by": str(updated_by),
                            "updated_at": updated_at.isoformat() if updated_at else None,
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
        "failover_policies": failover_policies,
        "failover_runtime": failover_runtime,
        "session_policies": session_policies,
        "session_runtime": session_runtime,
        "ws_policies": ws_policies,
        "ws_runtime": ws_runtime,
        "coverage_rows": coverage_rows,
        "backfill_recent": backfill_recent,
        "replay_recent": replay_recent,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/v1/control-panel/ingestion/kpi")
def control_panel_ingestion_kpi(
    x_control_panel_token: str | None = Header(default=None),
    target_1m_bars: int = Query(default=130000, ge=10000, le=300000),
    tick_sla_seconds: int = Query(default=120, ge=5, le=3600),
    row_limit: int = Query(default=200, ge=1, le=500),
) -> dict:
    session = get_operator_session(x_control_panel_token)
    metrics = {
        "target_1m_bars": int(target_1m_bars),
        "tick_sla_seconds": int(tick_sla_seconds),
        "active_markets": 0,
        "markets_meeting_ohlcv_target": 0,
        "markets_meeting_tick_sla": 0,
        "markets_meeting_both": 0,
        "avg_ohlcv_progress_pct": 0.0,
        "worst_tick_lag_seconds": 0,
    }
    rows: list[dict] = []
    mode = "online"
    try:
        with psycopg.connect(db_url()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    WITH markets AS (
                      SELECT lower(venue) AS venue, upper(symbol) AS symbol
                      FROM venue_market
                      WHERE enabled = TRUE
                        AND ingest_enabled = TRUE
                    ),
                    bars AS (
                      SELECT
                        lower(venue) AS venue,
                        upper(canonical_symbol) AS symbol,
                        COUNT(*)::bigint AS ohlcv_1m_count,
                        MAX(bucket_start) AS last_ohlcv_bucket
                      FROM ohlcv_bar
                      WHERE timeframe = '1m'
                      GROUP BY lower(venue), upper(canonical_symbol)
                    ),
                    ticks AS (
                      SELECT
                        lower(venue) AS venue,
                        upper(broker_symbol) AS symbol,
                        COUNT(*) FILTER (WHERE event_ts_received >= now() - interval '5 minutes')::bigint AS ticks_5m,
                        MAX(event_ts_received) AS last_tick_ts
                      FROM raw_tick
                      GROUP BY lower(venue), upper(broker_symbol)
                    )
                    SELECT
                      m.venue,
                      m.symbol,
                      COALESCE(b.ohlcv_1m_count, 0)::bigint AS ohlcv_1m_count,
                      b.last_ohlcv_bucket,
                      COALESCE(t.ticks_5m, 0)::bigint AS ticks_5m,
                      t.last_tick_ts,
                      CASE
                        WHEN t.last_tick_ts IS NULL THEN NULL
                        ELSE GREATEST(0, FLOOR(EXTRACT(EPOCH FROM (now() - t.last_tick_ts))))::bigint
                      END AS tick_lag_seconds
                    FROM markets m
                    LEFT JOIN bars b
                      ON b.venue = m.venue
                     AND b.symbol = m.symbol
                    LEFT JOIN ticks t
                      ON t.venue = m.venue
                     AND t.symbol = m.symbol
                    ORDER BY m.venue, m.symbol
                    LIMIT %s
                    """,
                    (row_limit,),
                )
                raw_rows = cur.fetchall()
        progress_sum = 0.0
        worst_tick_lag = 0
        for venue, symbol, ohlcv_count, last_ohlcv_bucket, ticks_5m, last_tick_ts, tick_lag in raw_rows:
            count = int(ohlcv_count or 0)
            progress = min(100.0, (count / max(1, target_1m_bars)) * 100.0)
            meets_ohlcv = count >= target_1m_bars
            lag_seconds = int(tick_lag) if tick_lag is not None else None
            meets_tick = lag_seconds is not None and lag_seconds <= tick_sla_seconds
            progress_sum += progress
            if lag_seconds is not None:
                worst_tick_lag = max(worst_tick_lag, lag_seconds)
            rows.append(
                {
                    "venue": str(venue),
                    "symbol": str(symbol),
                    "ohlcv_1m_count": count,
                    "ohlcv_target": int(target_1m_bars),
                    "ohlcv_progress_pct": round(progress, 2),
                    "ohlcv_missing": max(0, int(target_1m_bars) - count),
                    "last_ohlcv_bucket": last_ohlcv_bucket.isoformat() if last_ohlcv_bucket else None,
                    "ticks_5m": int(ticks_5m or 0),
                    "last_tick_ts": last_tick_ts.isoformat() if last_tick_ts else None,
                    "tick_lag_seconds": lag_seconds,
                    "tick_sla_seconds": int(tick_sla_seconds),
                    "meets_ohlcv_target": bool(meets_ohlcv),
                    "meets_tick_sla": bool(meets_tick),
                    "meets_both_kpi": bool(meets_ohlcv and meets_tick),
                }
            )
        total = len(rows)
        metrics["active_markets"] = total
        metrics["markets_meeting_ohlcv_target"] = sum(1 for row in rows if row["meets_ohlcv_target"])
        metrics["markets_meeting_tick_sla"] = sum(1 for row in rows if row["meets_tick_sla"])
        metrics["markets_meeting_both"] = sum(1 for row in rows if row["meets_both_kpi"])
        metrics["avg_ohlcv_progress_pct"] = round(progress_sum / total, 2) if total > 0 else 0.0
        metrics["worst_tick_lag_seconds"] = int(worst_tick_lag)
    except Exception:
        mode = "degraded"
        rows = []
    return {
        "service": "control-panel",
        "module": "ingestion-kpi",
        "mode": mode,
        "session": session,
        "metrics": metrics,
        "rows": rows,
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


@app.post("/api/v1/control-panel/ingestion/failover-policy")
def control_panel_ingestion_failover_policy_update(
    payload: dict = Body(...),
    x_control_panel_token: str | None = Header(default=None),
) -> dict:
    session = get_operator_session(x_control_panel_token)
    require_min_role(session["role"], "operator")

    venue = str(payload.get("venue", "")).strip().lower()
    if venue not in VALID_VENUES:
        raise HTTPException(status_code=400, detail="invalid venue")
    primary_endpoint = str(payload.get("primary_endpoint", "")).strip()
    if not primary_endpoint:
        raise HTTPException(status_code=400, detail="primary_endpoint is required")
    secondary_endpoints = parse_secondary_endpoints(payload.get("secondary_endpoints"))
    enabled = bool(payload.get("enabled", True))
    failure_threshold = int(payload.get("failure_threshold", 3))
    cooldown_seconds = int(payload.get("cooldown_seconds", 60))
    reconnect_backoff_seconds = int(payload.get("reconnect_backoff_seconds", 5))
    max_backoff_seconds = int(payload.get("max_backoff_seconds", 120))
    request_timeout_seconds = int(payload.get("request_timeout_seconds", VENUE_FETCH_TIMEOUT_SECS))
    jitter_pct = float(payload.get("jitter_pct", 0.2))
    justification = str(payload.get("justification", "")).strip()

    if len(justification) < 12:
        raise HTTPException(status_code=400, detail="justification must be at least 12 characters")
    if failure_threshold < 1 or failure_threshold > 20:
        raise HTTPException(status_code=400, detail="failure_threshold out of bounds")
    if cooldown_seconds < 1 or cooldown_seconds > 3600:
        raise HTTPException(status_code=400, detail="cooldown_seconds out of bounds")
    if reconnect_backoff_seconds < 1 or reconnect_backoff_seconds > 600:
        raise HTTPException(status_code=400, detail="reconnect_backoff_seconds out of bounds")
    if max_backoff_seconds < reconnect_backoff_seconds or max_backoff_seconds > 7200:
        raise HTTPException(status_code=400, detail="max_backoff_seconds out of bounds")
    if request_timeout_seconds < 1 or request_timeout_seconds > 120:
        raise HTTPException(status_code=400, detail="request_timeout_seconds out of bounds")
    if jitter_pct < 0.0 or jitter_pct > 1.0:
        raise HTTPException(status_code=400, detail="jitter_pct out of bounds")

    with psycopg.connect(db_url()) as conn:
        ensure_ingestion_failover_seed_data(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO control_panel_ingestion_failover_policy (
                  venue,
                  enabled,
                  primary_endpoint,
                  secondary_endpoints,
                  failure_threshold,
                  cooldown_seconds,
                  reconnect_backoff_seconds,
                  max_backoff_seconds,
                  request_timeout_seconds,
                  jitter_pct,
                  updated_by,
                  updated_at
                ) VALUES (
                  %s,
                  %s,
                  %s,
                  %s::jsonb,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  now()
                )
                ON CONFLICT (venue) DO UPDATE
                SET enabled = EXCLUDED.enabled,
                    primary_endpoint = EXCLUDED.primary_endpoint,
                    secondary_endpoints = EXCLUDED.secondary_endpoints,
                    failure_threshold = EXCLUDED.failure_threshold,
                    cooldown_seconds = EXCLUDED.cooldown_seconds,
                    reconnect_backoff_seconds = EXCLUDED.reconnect_backoff_seconds,
                    max_backoff_seconds = EXCLUDED.max_backoff_seconds,
                    request_timeout_seconds = EXCLUDED.request_timeout_seconds,
                    jitter_pct = EXCLUDED.jitter_pct,
                    updated_by = EXCLUDED.updated_by,
                    updated_at = now()
                """,
                (
                    venue,
                    enabled,
                    primary_endpoint,
                    json.dumps(secondary_endpoints),
                    failure_threshold,
                    cooldown_seconds,
                    reconnect_backoff_seconds,
                    max_backoff_seconds,
                    request_timeout_seconds,
                    jitter_pct,
                    str(session["user_id"]),
                ),
            )
        audit_control_panel_action(
            conn,
            user_id=session["user_id"],
            role=session["role"],
            action="ingestion.failover_policy.update",
            section="ingestion",
            target=venue,
            status="approved",
            reason=None,
            metadata={
                "justification": justification,
                "enabled": enabled,
                "primary_endpoint": primary_endpoint,
                "secondary_endpoints": secondary_endpoints,
                "failure_threshold": failure_threshold,
                "cooldown_seconds": cooldown_seconds,
                "reconnect_backoff_seconds": reconnect_backoff_seconds,
                "max_backoff_seconds": max_backoff_seconds,
                "request_timeout_seconds": request_timeout_seconds,
                "jitter_pct": jitter_pct,
            },
        )
        conn.commit()

    return {
        "status": "accepted",
        "session": session,
        "result": {
            "venue": venue,
            "enabled": enabled,
            "updated_by": str(session["user_id"]),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    }


@app.post("/api/v1/control-panel/ingestion/session-policy")
def control_panel_ingestion_session_policy_update(
    payload: dict = Body(...),
    x_control_panel_token: str | None = Header(default=None),
) -> dict:
    session = get_operator_session(x_control_panel_token)
    require_min_role(session["role"], "operator")

    venue = str(payload.get("venue", "")).strip().lower()
    if venue not in VALID_VENUES:
        raise HTTPException(status_code=400, detail="invalid venue")
    enabled = bool(payload.get("enabled", True))
    auth_mode = str(payload.get("auth_mode", "token")).strip().lower() or "token"
    token_ttl_seconds = int(payload.get("token_ttl_seconds", 1800))
    refresh_lead_seconds = int(payload.get("refresh_lead_seconds", 120))
    max_refresh_retries = int(payload.get("max_refresh_retries", 2))
    lockout_cooldown_seconds = int(payload.get("lockout_cooldown_seconds", 60))
    classify_401 = str(payload.get("classify_401", "session_expired")).strip()
    classify_403 = str(payload.get("classify_403", "permission_denied")).strip()
    classify_429 = str(payload.get("classify_429", "rate_limited")).strip()
    classify_5xx = str(payload.get("classify_5xx", "upstream_unavailable")).strip()
    justification = str(payload.get("justification", "")).strip()

    if len(justification) < 12:
        raise HTTPException(status_code=400, detail="justification must be at least 12 characters")
    if token_ttl_seconds < 60 or token_ttl_seconds > 86400:
        raise HTTPException(status_code=400, detail="token_ttl_seconds out of bounds")
    if refresh_lead_seconds < 10 or refresh_lead_seconds >= token_ttl_seconds:
        raise HTTPException(status_code=400, detail="refresh_lead_seconds out of bounds")
    if max_refresh_retries < 0 or max_refresh_retries > 20:
        raise HTTPException(status_code=400, detail="max_refresh_retries out of bounds")
    if lockout_cooldown_seconds < 1 or lockout_cooldown_seconds > 3600:
        raise HTTPException(status_code=400, detail="lockout_cooldown_seconds out of bounds")

    with psycopg.connect(db_url()) as conn:
        ensure_ingestion_session_seed_data(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO control_panel_ingestion_session_policy (
                  venue, enabled, auth_mode, token_ttl_seconds, refresh_lead_seconds,
                  max_refresh_retries, lockout_cooldown_seconds,
                  classify_401, classify_403, classify_429, classify_5xx,
                  updated_by, updated_at
                ) VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now()
                )
                ON CONFLICT (venue) DO UPDATE
                SET enabled = EXCLUDED.enabled,
                    auth_mode = EXCLUDED.auth_mode,
                    token_ttl_seconds = EXCLUDED.token_ttl_seconds,
                    refresh_lead_seconds = EXCLUDED.refresh_lead_seconds,
                    max_refresh_retries = EXCLUDED.max_refresh_retries,
                    lockout_cooldown_seconds = EXCLUDED.lockout_cooldown_seconds,
                    classify_401 = EXCLUDED.classify_401,
                    classify_403 = EXCLUDED.classify_403,
                    classify_429 = EXCLUDED.classify_429,
                    classify_5xx = EXCLUDED.classify_5xx,
                    updated_by = EXCLUDED.updated_by,
                    updated_at = now()
                """,
                (
                    venue,
                    enabled,
                    auth_mode,
                    token_ttl_seconds,
                    refresh_lead_seconds,
                    max_refresh_retries,
                    lockout_cooldown_seconds,
                    classify_401,
                    classify_403,
                    classify_429,
                    classify_5xx,
                    str(session["user_id"]),
                ),
            )
        audit_control_panel_action(
            conn,
            user_id=session["user_id"],
            role=session["role"],
            action="ingestion.session_policy.update",
            section="ingestion",
            target=venue,
            status="approved",
            reason=None,
            metadata={"justification": justification, "auth_mode": auth_mode, "enabled": enabled},
        )
        conn.commit()
    return {"status": "accepted", "session": session, "result": {"venue": venue, "enabled": enabled, "updated_by": str(session["user_id"])}}


@app.post("/api/v1/control-panel/ingestion/ws-policy")
def control_panel_ingestion_ws_policy_update(
    payload: dict = Body(...),
    x_control_panel_token: str | None = Header(default=None),
) -> dict:
    session = get_operator_session(x_control_panel_token)
    require_min_role(session["role"], "operator")

    venue = str(payload.get("venue", "")).strip().lower()
    if venue not in VALID_VENUES:
        raise HTTPException(status_code=400, detail="invalid venue")
    enabled = bool(payload.get("enabled", True))
    heartbeat_interval_seconds = int(payload.get("heartbeat_interval_seconds", 15))
    stale_after_seconds = int(payload.get("stale_after_seconds", 45))
    reconnect_backoff_seconds = int(payload.get("reconnect_backoff_seconds", 5))
    max_backoff_seconds = int(payload.get("max_backoff_seconds", 120))
    jitter_pct = float(payload.get("jitter_pct", 0.2))
    max_consecutive_failures = int(payload.get("max_consecutive_failures", 5))
    justification = str(payload.get("justification", "")).strip()

    if len(justification) < 12:
        raise HTTPException(status_code=400, detail="justification must be at least 12 characters")
    if heartbeat_interval_seconds < 3 or heartbeat_interval_seconds > 300:
        raise HTTPException(status_code=400, detail="heartbeat_interval_seconds out of bounds")
    if stale_after_seconds <= heartbeat_interval_seconds or stale_after_seconds > 1800:
        raise HTTPException(status_code=400, detail="stale_after_seconds out of bounds")
    if reconnect_backoff_seconds < 1 or reconnect_backoff_seconds > 600:
        raise HTTPException(status_code=400, detail="reconnect_backoff_seconds out of bounds")
    if max_backoff_seconds < reconnect_backoff_seconds or max_backoff_seconds > 7200:
        raise HTTPException(status_code=400, detail="max_backoff_seconds out of bounds")
    if jitter_pct < 0.0 or jitter_pct > 1.0:
        raise HTTPException(status_code=400, detail="jitter_pct out of bounds")
    if max_consecutive_failures < 1 or max_consecutive_failures > 100:
        raise HTTPException(status_code=400, detail="max_consecutive_failures out of bounds")

    with psycopg.connect(db_url()) as conn:
        ensure_ingestion_ws_seed_data(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO control_panel_ingestion_ws_policy (
                  venue, enabled, heartbeat_interval_seconds, stale_after_seconds,
                  reconnect_backoff_seconds, max_backoff_seconds, jitter_pct, max_consecutive_failures,
                  updated_by, updated_at
                ) VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s, now()
                )
                ON CONFLICT (venue) DO UPDATE
                SET enabled = EXCLUDED.enabled,
                    heartbeat_interval_seconds = EXCLUDED.heartbeat_interval_seconds,
                    stale_after_seconds = EXCLUDED.stale_after_seconds,
                    reconnect_backoff_seconds = EXCLUDED.reconnect_backoff_seconds,
                    max_backoff_seconds = EXCLUDED.max_backoff_seconds,
                    jitter_pct = EXCLUDED.jitter_pct,
                    max_consecutive_failures = EXCLUDED.max_consecutive_failures,
                    updated_by = EXCLUDED.updated_by,
                    updated_at = now()
                """,
                (
                    venue,
                    enabled,
                    heartbeat_interval_seconds,
                    stale_after_seconds,
                    reconnect_backoff_seconds,
                    max_backoff_seconds,
                    jitter_pct,
                    max_consecutive_failures,
                    str(session["user_id"]),
                ),
            )
        audit_control_panel_action(
            conn,
            user_id=session["user_id"],
            role=session["role"],
            action="ingestion.ws_policy.update",
            section="ingestion",
            target=venue,
            status="approved",
            reason=None,
            metadata={"justification": justification, "enabled": enabled},
        )
        conn.commit()
    return {"status": "accepted", "session": session, "result": {"venue": venue, "enabled": enabled, "updated_by": str(session["user_id"])}}


def ensure_control_panel_risk_limits_table(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS control_panel_risk_limits (
              limits_id UUID PRIMARY KEY,
              updated_by TEXT NOT NULL,
              min_confidence DOUBLE PRECISION NOT NULL,
              max_notional DOUBLE PRECISION NOT NULL,
              max_drawdown_pct DOUBLE PRECISION NOT NULL,
              max_symbol_exposure_notional DOUBLE PRECISION NOT NULL,
              max_portfolio_gross_exposure_notional DOUBLE PRECISION NOT NULL,
              min_available_equity DOUBLE PRECISION NOT NULL,
              created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_control_panel_risk_limits_created_at
              ON control_panel_risk_limits (created_at DESC)
            """
        )


def ensure_control_panel_ops_tables(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS control_panel_alert (
              alert_id UUID PRIMARY KEY,
              source TEXT NOT NULL,
              severity TEXT NOT NULL,
              title TEXT NOT NULL,
              status TEXT NOT NULL,
              owner TEXT,
              sla_due_at TIMESTAMPTZ,
              signal_ref TEXT,
              details JSONB NOT NULL DEFAULT '{}'::jsonb,
              created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
              updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_control_panel_alert_updated_at
              ON control_panel_alert (updated_at DESC)
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS control_panel_incident (
              incident_id UUID PRIMARY KEY,
              alert_id UUID REFERENCES control_panel_alert(alert_id) ON DELETE SET NULL,
              title TEXT NOT NULL,
              severity TEXT NOT NULL,
              status TEXT NOT NULL,
              owner TEXT,
              opened_at TIMESTAMPTZ NOT NULL DEFAULT now(),
              resolved_at TIMESTAMPTZ,
              timeline JSONB NOT NULL DEFAULT '[]'::jsonb,
              notes TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_control_panel_incident_opened_at
              ON control_panel_incident (opened_at DESC)
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS control_panel_runbook_execution (
              execution_id UUID PRIMARY KEY,
              incident_id UUID REFERENCES control_panel_incident(incident_id) ON DELETE SET NULL,
              runbook_code TEXT NOT NULL,
              action TEXT NOT NULL,
              status TEXT NOT NULL,
              triggered_by TEXT NOT NULL,
              justification TEXT NOT NULL,
              output JSONB NOT NULL DEFAULT '{}'::jsonb,
              created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_control_panel_runbook_execution_created_at
              ON control_panel_runbook_execution (created_at DESC)
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS control_panel_reconciliation_evidence (
              evidence_id UUID PRIMARY KEY,
              execution_id UUID REFERENCES control_panel_runbook_execution(execution_id) ON DELETE CASCADE,
              incident_id UUID REFERENCES control_panel_incident(incident_id) ON DELETE SET NULL,
              order_id UUID,
              correlation_id UUID,
              source TEXT NOT NULL,
              evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
              captured_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_control_panel_reconciliation_evidence_execution_ts
              ON control_panel_reconciliation_evidence (execution_id, captured_at DESC)
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_control_panel_reconciliation_evidence_order_ts
              ON control_panel_reconciliation_evidence (order_id, captured_at DESC)
            """
        )


def capture_runbook_reconciliation_evidence(
    conn: psycopg.Connection,
    execution_id: str,
    incident_id: str | None,
    order_id: str | None,
    correlation_id: str | None,
    lookback_minutes: int,
) -> dict:
    ensure_control_panel_ops_tables(conn)
    lookback = max(5, min(720, int(lookback_minutes)))
    summary = {
        "command_log_count": 0,
        "reconciliation_issue_count": 0,
        "incident_bundle_count": 0,
        "adapter_failure_classes": [],
        "lookback_minutes": lookback,
    }
    with conn.cursor() as cur:
        if order_id:
            cur.execute(
                """
                SELECT COALESCE(
                  jsonb_agg(to_jsonb(x) ORDER BY x.created_at DESC),
                  '[]'::jsonb
                )
                FROM (
                  SELECT command_id, order_id, action, accepted, reason, payload, created_at
                  FROM execution_command_log
                  WHERE order_id = %s::uuid
                    AND created_at >= now() - (%s || ' minutes')::interval
                  ORDER BY created_at DESC
                  LIMIT 50
                ) x
                """,
                (order_id, str(lookback)),
            )
            command_rows = cur.fetchone()[0] or []
            summary["command_log_count"] = len(command_rows)
            cur.execute(
                """
                INSERT INTO control_panel_reconciliation_evidence (
                  evidence_id, execution_id, incident_id, order_id, correlation_id, source, evidence
                ) VALUES (%s::uuid, %s::uuid, %s::uuid, %s::uuid, %s::uuid, 'execution_command_log', %s::jsonb)
                """,
                (
                    str(uuid.uuid4()),
                    execution_id,
                    incident_id,
                    order_id,
                    correlation_id,
                    json.dumps({"rows": command_rows}),
                ),
            )

        if correlation_id:
            cur.execute(
                """
                SELECT COALESCE(
                  jsonb_agg(to_jsonb(x) ORDER BY x.created_at DESC),
                  '[]'::jsonb
                )
                FROM (
                  SELECT audit_id, service_name, event_domain, event_type, correlation_id, venue, canonical_symbol, payload, created_at
                  FROM audit_event_log
                  WHERE correlation_id = %s::uuid
                    AND event_domain = 'execution'
                    AND created_at >= now() - (%s || ' minutes')::interval
                  ORDER BY created_at DESC
                  LIMIT 50
                ) x
                """,
                (correlation_id, str(lookback)),
            )
            issue_rows = cur.fetchone()[0] or []
            summary["reconciliation_issue_count"] = len(issue_rows)
            cur.execute(
                """
                INSERT INTO control_panel_reconciliation_evidence (
                  evidence_id, execution_id, incident_id, order_id, correlation_id, source, evidence
                ) VALUES (%s::uuid, %s::uuid, %s::uuid, %s::uuid, %s::uuid, 'audit_event_log', %s::jsonb)
                """,
                (
                    str(uuid.uuid4()),
                    execution_id,
                    incident_id,
                    order_id,
                    correlation_id,
                    json.dumps({"rows": issue_rows}),
                ),
            )

            cur.execute(
                """
                SELECT COALESCE(
                  jsonb_agg(to_jsonb(x) ORDER BY x.exported_at DESC),
                  '[]'::jsonb
                )
                FROM (
                  SELECT bundle_id, exported_at, taxonomy_version, correlation_id, order_id, venue, canonical_symbol, lineage, artifacts
                  FROM incident_evidence_bundle
                  WHERE correlation_id = %s::uuid
                    AND exported_at >= now() - (%s || ' minutes')::interval
                  ORDER BY exported_at DESC
                  LIMIT 10
                ) x
                """,
                (correlation_id, str(lookback)),
            )
            bundle_rows = cur.fetchone()[0] or []
            summary["incident_bundle_count"] = len(bundle_rows)
            cur.execute(
                """
                INSERT INTO control_panel_reconciliation_evidence (
                  evidence_id, execution_id, incident_id, order_id, correlation_id, source, evidence
                ) VALUES (%s::uuid, %s::uuid, %s::uuid, %s::uuid, %s::uuid, 'incident_evidence_bundle', %s::jsonb)
                """,
                (
                    str(uuid.uuid4()),
                    execution_id,
                    incident_id,
                    order_id,
                    correlation_id,
                    json.dumps({"rows": bundle_rows}),
                ),
            )

        cur.execute(
            """
            SELECT COALESCE(
              jsonb_agg(DISTINCT cls),
              '[]'::jsonb
            )
            FROM (
              SELECT payload->>'failure_class' AS cls
              FROM execution_command_log
              WHERE payload ? 'failure_class'
                AND payload->>'failure_class' IS NOT NULL
                AND payload->>'failure_class' <> ''
                AND (%s::uuid IS NULL OR order_id = %s::uuid)
                AND created_at >= now() - (%s || ' minutes')::interval
            ) classes
            """,
            (order_id, order_id, str(lookback)),
        )
        summary["adapter_failure_classes"] = cur.fetchone()[0] or []
    return summary


def ensure_control_panel_research_tables(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS control_panel_dataset_registry (
              dataset_id UUID PRIMARY KEY,
              dataset_code TEXT NOT NULL UNIQUE,
              venue TEXT NOT NULL,
              symbol TEXT NOT NULL,
              timeframe TEXT NOT NULL,
              row_count BIGINT NOT NULL DEFAULT 0,
              start_ts TIMESTAMPTZ,
              end_ts TIMESTAMPTZ,
              lineage_ref TEXT,
              status TEXT NOT NULL DEFAULT 'ready',
              created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
              updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS control_panel_backtest_run (
              run_id UUID PRIMARY KEY,
              dataset_id UUID REFERENCES control_panel_dataset_registry(dataset_id) ON DELETE SET NULL,
              strategy_code TEXT NOT NULL,
              model_version TEXT,
              status TEXT NOT NULL,
              pnl DOUBLE PRECISION NOT NULL DEFAULT 0,
              sharpe DOUBLE PRECISION NOT NULL DEFAULT 0,
              max_drawdown_pct DOUBLE PRECISION NOT NULL DEFAULT 0,
              params JSONB NOT NULL DEFAULT '{}'::jsonb,
              triggered_by TEXT NOT NULL,
              created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
              completed_at TIMESTAMPTZ
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS control_panel_model_registry (
              model_id UUID PRIMARY KEY,
              model_name TEXT NOT NULL,
              model_version TEXT NOT NULL,
              experiment_ref TEXT,
              stage TEXT NOT NULL,
              readiness_score DOUBLE PRECISION NOT NULL DEFAULT 0,
              gate_status TEXT NOT NULL DEFAULT 'pending',
              metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
              created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
              updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
              UNIQUE (model_name, model_version)
            )
            """
        )


def ensure_research_seed_data(conn: psycopg.Connection) -> None:
    ensure_control_panel_research_tables(conn)
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM control_panel_dataset_registry")
        if int(cur.fetchone()[0] or 0) == 0:
            cur.execute(
                """
                INSERT INTO control_panel_dataset_registry (
                  dataset_id, dataset_code, venue, symbol, timeframe, row_count, start_ts, end_ts, lineage_ref, status
                ) VALUES
                (%s::uuid, 'DS-COINBASE-BTCUSD-1M-90D', 'coinbase', 'BTCUSD', '1m', 129600, now() - interval '90 days', now(), 'ohlcv_bar:coinbase:BTCUSD:1m', 'ready'),
                (%s::uuid, 'DS-OANDA-EURUSD-1M-90D', 'oanda', 'EURUSD', '1m', 129600, now() - interval '90 days', now(), 'ohlcv_bar:oanda:EURUSD:1m', 'ready')
                """,
                (str(uuid.uuid4()), str(uuid.uuid4())),
            )


def ensure_control_panel_config_tables(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS control_panel_config_registry (
              config_key TEXT PRIMARY KEY,
              environment TEXT NOT NULL,
              config_value JSONB NOT NULL DEFAULT '{}'::jsonb,
              value_type TEXT NOT NULL,
              risk_level TEXT NOT NULL DEFAULT 'medium',
              min_role TEXT NOT NULL DEFAULT 'operator',
              schema_ref TEXT,
              updated_by TEXT NOT NULL,
              updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS control_panel_config_change_request (
              change_id UUID PRIMARY KEY,
              config_key TEXT NOT NULL,
              environment TEXT NOT NULL,
              proposed_value JSONB NOT NULL,
              previous_value JSONB NOT NULL,
              status TEXT NOT NULL,
              requested_by TEXT NOT NULL,
              approved_by TEXT,
              justification TEXT NOT NULL,
              created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
              decided_at TIMESTAMPTZ
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS control_panel_config_change_history (
              history_id UUID PRIMARY KEY,
              change_id UUID NOT NULL,
              action TEXT NOT NULL,
              actor TEXT NOT NULL,
              metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
              created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )


def ensure_config_seed_data(conn: psycopg.Connection) -> None:
    ensure_control_panel_config_tables(conn)
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM control_panel_config_registry")
        if int(cur.fetchone()[0] or 0) > 0:
            return
        cur.execute(
            """
            INSERT INTO control_panel_config_registry (
              config_key, environment, config_value, value_type, risk_level, min_role, schema_ref, updated_by
            ) VALUES
            ('risk.max_notional', 'dev', '100000'::jsonb, 'number', 'high', 'risk_manager', 'risk_limits.v1', 'seed'),
            ('risk.max_notional', 'paper', '90000'::jsonb, 'number', 'high', 'risk_manager', 'risk_limits.v1', 'seed'),
            ('risk.max_notional', 'prod', '75000'::jsonb, 'number', 'high', 'admin', 'risk_limits.v1', 'seed'),
            ('execution.default_tif', 'dev', '\"GTC\"'::jsonb, 'string', 'low', 'operator', 'execution_config.v1', 'seed'),
            ('execution.default_tif', 'paper', '\"GTC\"'::jsonb, 'string', 'low', 'operator', 'execution_config.v1', 'seed'),
            ('execution.default_tif', 'prod', '\"IOC\"'::jsonb, 'string', 'medium', 'risk_manager', 'execution_config.v1', 'seed'),
            ('alerts.sla_minutes_default', 'dev', '30'::jsonb, 'number', 'low', 'operator', 'ops_alerts.v1', 'seed'),
            ('alerts.sla_minutes_default', 'paper', '20'::jsonb, 'number', 'low', 'operator', 'ops_alerts.v1', 'seed'),
            ('alerts.sla_minutes_default', 'prod', '15'::jsonb, 'number', 'medium', 'risk_manager', 'ops_alerts.v1', 'seed')
            """
        )


def ensure_control_panel_ingestion_failover_policy_table(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS control_panel_ingestion_failover_policy (
              venue TEXT PRIMARY KEY,
              enabled BOOLEAN NOT NULL DEFAULT TRUE,
              primary_endpoint TEXT NOT NULL,
              secondary_endpoints JSONB NOT NULL DEFAULT '[]'::jsonb,
              failure_threshold INTEGER NOT NULL DEFAULT 3,
              cooldown_seconds INTEGER NOT NULL DEFAULT 60,
              reconnect_backoff_seconds INTEGER NOT NULL DEFAULT 5,
              max_backoff_seconds INTEGER NOT NULL DEFAULT 120,
              request_timeout_seconds INTEGER NOT NULL DEFAULT 8,
              jitter_pct DOUBLE PRECISION NOT NULL DEFAULT 0.2,
              updated_by TEXT NOT NULL,
              updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )


def ensure_control_panel_ingestion_session_policy_table(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS control_panel_ingestion_session_policy (
              venue TEXT PRIMARY KEY,
              enabled BOOLEAN NOT NULL DEFAULT TRUE,
              auth_mode TEXT NOT NULL DEFAULT 'token',
              token_ttl_seconds INTEGER NOT NULL DEFAULT 1800,
              refresh_lead_seconds INTEGER NOT NULL DEFAULT 120,
              max_refresh_retries INTEGER NOT NULL DEFAULT 2,
              lockout_cooldown_seconds INTEGER NOT NULL DEFAULT 60,
              classify_401 TEXT NOT NULL DEFAULT 'session_expired',
              classify_403 TEXT NOT NULL DEFAULT 'permission_denied',
              classify_429 TEXT NOT NULL DEFAULT 'rate_limited',
              classify_5xx TEXT NOT NULL DEFAULT 'upstream_unavailable',
              updated_by TEXT NOT NULL,
              updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )


def ensure_control_panel_ingestion_ws_policy_table(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS control_panel_ingestion_ws_policy (
              venue TEXT PRIMARY KEY,
              enabled BOOLEAN NOT NULL DEFAULT TRUE,
              heartbeat_interval_seconds INTEGER NOT NULL DEFAULT 15,
              stale_after_seconds INTEGER NOT NULL DEFAULT 45,
              reconnect_backoff_seconds INTEGER NOT NULL DEFAULT 5,
              max_backoff_seconds INTEGER NOT NULL DEFAULT 120,
              jitter_pct DOUBLE PRECISION NOT NULL DEFAULT 0.2,
              max_consecutive_failures INTEGER NOT NULL DEFAULT 5,
              updated_by TEXT NOT NULL,
              updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )


def ensure_ingestion_failover_seed_data(conn: psycopg.Connection) -> None:
    ensure_control_panel_ingestion_failover_policy_table(conn)
    defaults = {
        "oanda": {
            "primary_endpoint": OANDA_REST_URL,
            "secondary_endpoints": [],
            "request_timeout_seconds": VENUE_FETCH_TIMEOUT_SECS,
        },
        "capital": {
            "primary_endpoint": env("CAPITAL_API_URL", "https://api-capital.backend-capital.com"),
            "secondary_endpoints": [],
            "request_timeout_seconds": VENUE_FETCH_TIMEOUT_SECS,
        },
        "coinbase": {
            "primary_endpoint": COINBASE_REST_URL,
            "secondary_endpoints": [COINBASE_PUBLIC_REST_URL] if COINBASE_PUBLIC_REST_URL else [],
            "request_timeout_seconds": VENUE_FETCH_TIMEOUT_SECS,
        },
    }
    with conn.cursor() as cur:
        for venue, cfg in defaults.items():
            cur.execute(
                """
                INSERT INTO control_panel_ingestion_failover_policy (
                  venue,
                  enabled,
                  primary_endpoint,
                  secondary_endpoints,
                  failure_threshold,
                  cooldown_seconds,
                  reconnect_backoff_seconds,
                  max_backoff_seconds,
                  request_timeout_seconds,
                  jitter_pct,
                  updated_by
                ) VALUES (
                  %s,
                  TRUE,
                  %s,
                  %s::jsonb,
                  3,
                  60,
                  5,
                  120,
                  %s,
                  0.2,
                  'seed'
                )
                ON CONFLICT (venue) DO NOTHING
                """,
                (
                    venue,
                    str(cfg["primary_endpoint"]),
                    json.dumps(cfg["secondary_endpoints"]),
                    int(cfg["request_timeout_seconds"]),
                ),
            )


def ensure_ingestion_session_seed_data(conn: psycopg.Connection) -> None:
    ensure_control_panel_ingestion_session_policy_table(conn)
    with conn.cursor() as cur:
        for venue in sorted(VALID_VENUES):
            cur.execute(
                """
                INSERT INTO control_panel_ingestion_session_policy (
                  venue, enabled, auth_mode, token_ttl_seconds, refresh_lead_seconds,
                  max_refresh_retries, lockout_cooldown_seconds,
                  classify_401, classify_403, classify_429, classify_5xx, updated_by
                ) VALUES (
                  %s, TRUE, 'token', 1800, 120, 2, 60,
                  'session_expired', 'permission_denied', 'rate_limited', 'upstream_unavailable', 'seed'
                )
                ON CONFLICT (venue) DO NOTHING
                """,
                (venue,),
            )


def ensure_ingestion_ws_seed_data(conn: psycopg.Connection) -> None:
    ensure_control_panel_ingestion_ws_policy_table(conn)
    with conn.cursor() as cur:
        for venue in sorted(VALID_VENUES):
            cur.execute(
                """
                INSERT INTO control_panel_ingestion_ws_policy (
                  venue, enabled, heartbeat_interval_seconds, stale_after_seconds,
                  reconnect_backoff_seconds, max_backoff_seconds, jitter_pct, max_consecutive_failures, updated_by
                ) VALUES (
                  %s, TRUE, 15, 45, 5, 120, 0.2, 5, 'seed'
                )
                ON CONFLICT (venue) DO NOTHING
                """,
                (venue,),
            )


def parse_secondary_endpoints(raw: object) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        return [item.strip() for item in raw.split(",") if item.strip()]
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    raise HTTPException(status_code=400, detail="secondary_endpoints must be string or list")


def ingestion_failover_runtime(conn: psycopg.Connection) -> dict:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
              COUNT(*) FILTER (WHERE enabled = TRUE),
              COUNT(*) FILTER (WHERE enabled = FALSE),
              COALESCE(MAX(updated_at), now())
            FROM control_panel_ingestion_failover_policy
            """
        )
        enabled_count, disabled_count, updated_at = cur.fetchone()
        cur.execute(
            """
            SELECT venue, enabled, ingest_enabled
            FROM venue_market
            LIMIT 1000
            """
        )
        market_rows = cur.fetchall()

    active_market_venues: set[str] = set()
    degraded_market_venues: set[str] = set()
    for venue, enabled, ingest_enabled in market_rows:
        venue_name = str(venue).lower()
        if bool(enabled) and bool(ingest_enabled):
            active_market_venues.add(venue_name)
        else:
            degraded_market_venues.add(venue_name)

    return {
        "configured_enabled_venues": int(enabled_count or 0),
        "configured_disabled_venues": int(disabled_count or 0),
        "active_market_venues": sorted(active_market_venues),
        "degraded_market_venues": sorted(degraded_market_venues),
        "updated_at": updated_at.isoformat() if updated_at else None,
    }


def ingestion_session_runtime(conn: psycopg.Connection) -> dict:
    ensure_ingestion_session_seed_data(conn)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
              COUNT(*) FILTER (WHERE enabled = TRUE),
              COUNT(*) FILTER (WHERE enabled = FALSE),
              COALESCE(MAX(updated_at), now())
            FROM control_panel_ingestion_session_policy
            """
        )
        enabled_count, disabled_count, updated_at = cur.fetchone()
    capital_expires_in = None
    if _CAPITAL_SESSION_EXPIRY is not None:
        capital_expires_in = max(0, int((_CAPITAL_SESSION_EXPIRY - datetime.now(timezone.utc)).total_seconds()))
    return {
        "configured_enabled_venues": int(enabled_count or 0),
        "configured_disabled_venues": int(disabled_count or 0),
        "capital_session_cached": bool(_CAPITAL_SESSION_HEADERS),
        "capital_session_expires_in_seconds": capital_expires_in,
        "updated_at": updated_at.isoformat() if updated_at else None,
    }


def ingestion_ws_runtime(conn: psycopg.Connection) -> dict:
    ensure_ingestion_ws_seed_data(conn)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
              COUNT(*) FILTER (WHERE enabled = TRUE),
              COUNT(*) FILTER (WHERE enabled = FALSE),
              COALESCE(MAX(updated_at), now())
            FROM control_panel_ingestion_ws_policy
            """
        )
        enabled_count, disabled_count, updated_at = cur.fetchone()
        cur.execute(
            """
            SELECT COUNT(*)
            FROM venue_market
            WHERE enabled = TRUE
              AND ingest_enabled = TRUE
            """
        )
        active_markets = int(cur.fetchone()[0] or 0)
    return {
        "configured_enabled_venues": int(enabled_count or 0),
        "configured_disabled_venues": int(disabled_count or 0),
        "active_markets": active_markets,
        "updated_at": updated_at.isoformat() if updated_at else None,
    }


def validate_typed_config(value_type: str, value: object) -> bool:
    if value_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if value_type == "boolean":
        return isinstance(value, bool)
    if value_type == "string":
        return isinstance(value, str) and len(value.strip()) > 0
    return False


def load_current_risk_limits(conn: psycopg.Connection) -> dict:
    ensure_control_panel_risk_limits_table(conn)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
              min_confidence,
              max_notional,
              max_drawdown_pct,
              max_symbol_exposure_notional,
              max_portfolio_gross_exposure_notional,
              min_available_equity,
              updated_by,
              created_at
            FROM control_panel_risk_limits
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
        row = cur.fetchone()
    if row:
        return {
            "min_confidence": float(row[0]),
            "max_notional": float(row[1]),
            "max_drawdown_pct": float(row[2]),
            "max_symbol_exposure_notional": float(row[3]),
            "max_portfolio_gross_exposure_notional": float(row[4]),
            "min_available_equity": float(row[5]),
            "updated_by": str(row[6]),
            "updated_at": row[7].isoformat() if row[7] else None,
            "source": "control_panel",
        }
    return {
        "min_confidence": env_f64_or("RISK_MIN_CONFIDENCE", 0.55),
        "max_notional": env_f64_or("RISK_MAX_NOTIONAL", 100000.0),
        "max_drawdown_pct": env_f64_or("RISK_MAX_DRAWDOWN_PCT", 5.0),
        "max_symbol_exposure_notional": env_f64_or("RISK_MAX_SYMBOL_EXPOSURE_NOTIONAL", 250000.0),
        "max_portfolio_gross_exposure_notional": env_f64_or(
            "RISK_MAX_PORTFOLIO_GROSS_EXPOSURE_NOTIONAL", 500000.0
        ),
        "min_available_equity": env_f64_or("RISK_MIN_AVAILABLE_EQUITY", 10000.0),
        "updated_by": "env_default",
        "updated_at": None,
        "source": "env_default",
    }


@app.get("/api/v1/control-panel/risk-portfolio")
def control_panel_risk_portfolio(
    x_control_panel_token: str | None = Header(default=None),
    row_limit: int = Query(default=25, ge=1, le=200),
) -> dict:
    session = get_operator_session(x_control_panel_token)
    metrics = {
        "policy_violations_24h": 0,
        "risk_decisions_24h": 0,
        "kill_switch_on_symbols": 0,
        "portfolio_gross_exposure": 0.0,
        "portfolio_net_exposure": 0.0,
        "available_equity_headroom": 0.0,
    }
    strategy_rows: list[dict] = []
    symbol_exposure_rows: list[dict] = []
    recent_violations: list[dict] = []
    limits: dict = {}
    mode = "online"

    try:
        with psycopg.connect(db_url()) as conn:
            limits = load_current_risk_limits(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                      COUNT(*) FILTER (WHERE approved = FALSE AND jsonb_array_length(violations) > 0) AS violations_24h,
                      COUNT(*) AS decisions_24h
                    FROM risk_decision_log
                    WHERE created_at >= now() - interval '24 hours'
                    """
                )
                row = cur.fetchone()
                metrics["policy_violations_24h"] = int(row[0] or 0)
                metrics["risk_decisions_24h"] = int(row[1] or 0)

                cur.execute(
                    "SELECT COUNT(*) FROM risk_state WHERE kill_switch_enabled = TRUE"
                )
                metrics["kill_switch_on_symbols"] = int(cur.fetchone()[0] or 0)

                cur.execute(
                    """
                    SELECT COALESCE(gross_exposure_notional, 0), COALESCE(net_exposure_notional, 0), COALESCE(equity, 0)
                    FROM portfolio_account_state
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """
                )
                row = cur.fetchone()
                if row:
                    gross = float(row[0] or 0.0)
                    net = float(row[1] or 0.0)
                    equity = float(row[2] or 0.0)
                    metrics["portfolio_gross_exposure"] = gross
                    metrics["portfolio_net_exposure"] = net
                    metrics["available_equity_headroom"] = max(0.0, equity - gross)

                cur.execute(
                    """
                    SELECT venue, canonical_symbol, timeframe, current_exposure_notional, drawdown_pct, kill_switch_enabled, updated_at
                    FROM risk_state
                    ORDER BY updated_at DESC
                    LIMIT %s
                    """,
                    (row_limit,),
                )
                for r in cur.fetchall():
                    symbol_exposure_rows.append(
                        {
                            "venue": str(r[0]),
                            "symbol": str(r[1]),
                            "timeframe": str(r[2]),
                            "exposure_notional": float(r[3] or 0.0),
                            "drawdown_pct": float(r[4] or 0.0),
                            "kill_switch_enabled": bool(r[5]),
                            "updated_at": r[6].isoformat() if r[6] else None,
                        }
                    )

                cur.execute(
                    """
                    SELECT
                      venue,
                      canonical_symbol,
                      COUNT(*) AS decisions_24h,
                      AVG(confidence) AS avg_confidence,
                      COUNT(*) FILTER (WHERE approved = FALSE AND jsonb_array_length(violations) > 0) AS violations_24h
                    FROM risk_decision_log
                    WHERE created_at >= now() - interval '24 hours'
                    GROUP BY venue, canonical_symbol
                    ORDER BY decisions_24h DESC
                    LIMIT %s
                    """,
                    (row_limit,),
                )
                for r in cur.fetchall():
                    strategy_rows.append(
                        {
                            "venue": str(r[0]),
                            "symbol": str(r[1]),
                            "decisions_24h": int(r[2] or 0),
                            "avg_confidence": float(r[3] or 0.0),
                            "violations_24h": int(r[4] or 0),
                            "status": "degraded" if int(r[4] or 0) > 0 else "healthy",
                        }
                    )

                cur.execute(
                    """
                    SELECT venue, canonical_symbol, reason, violations, created_at
                    FROM risk_decision_log
                    WHERE approved = FALSE
                      AND jsonb_array_length(violations) > 0
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (row_limit,),
                )
                for r in cur.fetchall():
                    recent_violations.append(
                        {
                            "venue": str(r[0]),
                            "symbol": str(r[1]),
                            "reason": str(r[2]),
                            "violations": r[3] if isinstance(r[3], list) else [],
                            "created_at": r[4].isoformat() if r[4] else None,
                        }
                    )
    except Exception:
        mode = "degraded"

    return {
        "service": "control-panel",
        "module": "risk-portfolio",
        "mode": mode,
        "session": session,
        "metrics": metrics,
        "limits": limits,
        "strategy_rows": strategy_rows,
        "symbol_exposure_rows": symbol_exposure_rows,
        "recent_violations": recent_violations,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/v1/control-panel/risk-limits")
def control_panel_risk_limits_update(
    payload: dict = Body(...),
    x_control_panel_token: str | None = Header(default=None),
) -> dict:
    session = get_operator_session(x_control_panel_token)
    require_min_role(session["role"], "risk_manager")
    justification = str(payload.get("justification", "")).strip()
    if len(justification) < 12:
        raise HTTPException(status_code=400, detail="justification must be at least 12 characters")

    min_confidence = float(payload.get("min_confidence", env_f64_or("RISK_MIN_CONFIDENCE", 0.55)))
    max_notional = float(payload.get("max_notional", env_f64_or("RISK_MAX_NOTIONAL", 100000.0)))
    max_drawdown_pct = float(payload.get("max_drawdown_pct", env_f64_or("RISK_MAX_DRAWDOWN_PCT", 5.0)))
    max_symbol_exposure_notional = float(
        payload.get("max_symbol_exposure_notional", env_f64_or("RISK_MAX_SYMBOL_EXPOSURE_NOTIONAL", 250000.0))
    )
    max_portfolio_gross_exposure_notional = float(
        payload.get(
            "max_portfolio_gross_exposure_notional",
            env_f64_or("RISK_MAX_PORTFOLIO_GROSS_EXPOSURE_NOTIONAL", 500000.0),
        )
    )
    min_available_equity = float(payload.get("min_available_equity", env_f64_or("RISK_MIN_AVAILABLE_EQUITY", 10000.0)))

    if not (0.0 <= min_confidence <= 1.0):
        raise HTTPException(status_code=400, detail="min_confidence must be between 0 and 1")
    if max_notional <= 0 or max_symbol_exposure_notional <= 0 or max_portfolio_gross_exposure_notional <= 0:
        raise HTTPException(status_code=400, detail="notional limits must be positive")
    if max_drawdown_pct < 0 or min_available_equity < 0:
        raise HTTPException(status_code=400, detail="drawdown/equity limits must be non-negative")

    limits = {
        "min_confidence": min_confidence,
        "max_notional": max_notional,
        "max_drawdown_pct": max_drawdown_pct,
        "max_symbol_exposure_notional": max_symbol_exposure_notional,
        "max_portfolio_gross_exposure_notional": max_portfolio_gross_exposure_notional,
        "min_available_equity": min_available_equity,
    }
    with psycopg.connect(db_url()) as conn:
        ensure_control_panel_risk_limits_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO control_panel_risk_limits (
                  limits_id, updated_by, min_confidence, max_notional, max_drawdown_pct,
                  max_symbol_exposure_notional, max_portfolio_gross_exposure_notional, min_available_equity
                ) VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(uuid.uuid4()),
                    session["user_id"],
                    min_confidence,
                    max_notional,
                    max_drawdown_pct,
                    max_symbol_exposure_notional,
                    max_portfolio_gross_exposure_notional,
                    min_available_equity,
                ),
            )
        audit_control_panel_action(
            conn,
            user_id=session["user_id"],
            role=session["role"],
            action="risk.update_limits",
            section="risk",
            target="global",
            status="approved",
            reason=None,
            metadata={"justification": justification, **limits},
        )
        conn.commit()

    return {"status": "updated", "limits": limits, "updated_by": session["user_id"]}


@app.post("/api/v1/control-panel/risk/kill-switch")
def control_panel_risk_kill_switch(
    payload: dict = Body(...),
    x_control_panel_token: str | None = Header(default=None),
) -> dict:
    session = get_operator_session(x_control_panel_token)
    require_min_role(session["role"], "risk_manager")
    enabled = bool(payload.get("enabled", False))
    scope = str(payload.get("scope", "global")).strip().lower()
    venue = str(payload.get("venue", "")).strip().lower()
    symbol = str(payload.get("symbol", "")).strip().upper()
    timeframe = str(payload.get("timeframe", "1m")).strip()
    justification = str(payload.get("justification", "")).strip()
    if len(justification) < 12:
        raise HTTPException(status_code=400, detail="justification must be at least 12 characters")
    if scope not in {"global", "market"}:
        raise HTTPException(status_code=400, detail="scope must be global or market")
    if scope == "market" and (not venue or not symbol):
        raise HTTPException(status_code=400, detail="venue and symbol required for market scope")

    affected_rows = 0
    with psycopg.connect(db_url()) as conn:
        with conn.cursor() as cur:
            if scope == "global":
                cur.execute(
                    """
                    UPDATE risk_state
                    SET kill_switch_enabled = %s, updated_at = now()
                    """,
                    (enabled,),
                )
                affected_rows = int(cur.rowcount or 0)
            else:
                cur.execute(
                    """
                    UPDATE risk_state
                    SET kill_switch_enabled = %s, updated_at = now()
                    WHERE venue = %s AND canonical_symbol = %s AND timeframe = %s
                    """,
                    (enabled, venue, symbol, timeframe),
                )
                affected_rows = int(cur.rowcount or 0)

        audit_control_panel_action(
            conn,
            user_id=session["user_id"],
            role=session["role"],
            action="risk.kill_switch",
            section="risk",
            target=f"{scope}:{venue}:{symbol}:{timeframe}",
            status="approved",
            reason=None,
            metadata={"enabled": enabled, "scope": scope, "justification": justification, "affected_rows": affected_rows},
        )
        conn.commit()

    return {"status": "updated", "enabled": enabled, "scope": scope, "affected_rows": affected_rows}


@app.get("/api/v1/control-panel/execution")
def control_panel_execution(
    x_control_panel_token: str | None = Header(default=None),
    row_limit: int = Query(default=30, ge=1, le=200),
) -> dict:
    session = get_operator_session(x_control_panel_token)
    metrics = {
        "orders_total": 0,
        "submitted_24h": 0,
        "filled_24h": 0,
        "rejected_24h": 0,
        "cancelled_24h": 0,
        "reconciliation_issues_open": 0,
    }
    order_rows: list[dict] = []
    command_rows: list[dict] = []
    reconciliation_rows: list[dict] = []
    broker_diagnostics: list[dict] = []
    mode = "online"

    try:
        with psycopg.connect(db_url()) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM execution_order_journal")
                metrics["orders_total"] = int(cur.fetchone()[0] or 0)

                cur.execute(
                    """
                    SELECT
                      COUNT(*) FILTER (WHERE status = 'submitted' AND updated_at >= now() - interval '24 hours'),
                      COUNT(*) FILTER (WHERE status = 'filled' AND updated_at >= now() - interval '24 hours'),
                      COUNT(*) FILTER (WHERE status IN ('rejected', 'rejected_by_broker', 'rejected_by_risk') AND updated_at >= now() - interval '24 hours'),
                      COUNT(*) FILTER (WHERE status IN ('cancelled', 'cancel_requested') AND updated_at >= now() - interval '24 hours')
                    FROM execution_order_journal
                    """
                )
                row = cur.fetchone()
                metrics["submitted_24h"] = int(row[0] or 0)
                metrics["filled_24h"] = int(row[1] or 0)
                metrics["rejected_24h"] = int(row[2] or 0)
                metrics["cancelled_24h"] = int(row[3] or 0)

                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM execution_order_journal
                    WHERE status IN ('rejected', 'rejected_by_broker', 'cancelled')
                    """
                )
                metrics["reconciliation_issues_open"] = int(cur.fetchone()[0] or 0)

                cur.execute(
                    """
                    SELECT
                      order_id,
                      venue,
                      canonical_symbol,
                      side,
                      status,
                      broker_order_id,
                      requested_notional,
                      updated_at
                    FROM execution_order_journal
                    ORDER BY updated_at DESC
                    LIMIT %s
                    """,
                    (row_limit,),
                )
                for r in cur.fetchall():
                    order_rows.append(
                        {
                            "order_id": str(r[0]),
                            "venue": str(r[1]),
                            "symbol": str(r[2]),
                            "side": str(r[3]),
                            "status": str(r[4]),
                            "broker_order_id": r[5],
                            "requested_notional": float(r[6] or 0.0),
                            "updated_at": r[7].isoformat() if r[7] else None,
                        }
                    )

                cur.execute(
                    """
                    SELECT
                      command_id,
                      order_id,
                      action,
                      accepted,
                      reason,
                      created_at
                    FROM execution_command_log
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (row_limit,),
                )
                for r in cur.fetchall():
                    command_rows.append(
                        {
                            "command_id": str(r[0]),
                            "order_id": str(r[1]),
                            "action": str(r[2]),
                            "accepted": bool(r[3]),
                            "reason": r[4],
                            "created_at": r[5].isoformat() if r[5] else None,
                        }
                    )

                cur.execute(
                    """
                    SELECT
                      order_id,
                      venue,
                      canonical_symbol,
                      status,
                      updated_at
                    FROM execution_order_journal
                    WHERE status IN ('rejected', 'rejected_by_broker', 'cancelled')
                    ORDER BY updated_at DESC
                    LIMIT %s
                    """,
                    (row_limit,),
                )
                for r in cur.fetchall():
                    reconciliation_rows.append(
                        {
                            "order_id": str(r[0]),
                            "venue": str(r[1]),
                            "symbol": str(r[2]),
                            "status": str(r[3]),
                            "updated_at": r[4].isoformat() if r[4] else None,
                        }
                    )

                cur.execute(
                    """
                    SELECT event_type, COUNT(*)::bigint
                    FROM audit_event_log
                    WHERE event_domain = 'execution'
                      AND created_at >= now() - interval '24 hours'
                    GROUP BY event_type
                    ORDER BY COUNT(*) DESC, event_type ASC
                    LIMIT %s
                    """,
                    (row_limit,),
                )
                for event_type, count in cur.fetchall():
                    broker_diagnostics.append(
                        {
                            "event_type": str(event_type),
                            "count_24h": int(count or 0),
                        }
                    )
    except Exception:
        mode = "degraded"

    return {
        "service": "control-panel",
        "module": "execution",
        "mode": mode,
        "session": session,
        "metrics": metrics,
        "order_rows": order_rows,
        "command_rows": command_rows,
        "reconciliation_rows": reconciliation_rows,
        "broker_diagnostics": broker_diagnostics,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/v1/control-panel/execution/command")
def control_panel_execution_command(
    payload: dict = Body(...),
    x_control_panel_token: str | None = Header(default=None),
) -> dict:
    session = get_operator_session(x_control_panel_token)
    require_min_role(session["role"], "operator")
    justification = str(payload.get("justification", "")).strip()
    if len(justification) < 12:
        raise HTTPException(status_code=400, detail="justification must be at least 12 characters")

    order_id = str(payload.get("order_id", "")).strip()
    action = str(payload.get("action", "")).strip().lower()
    if action not in {"amend", "cancel"}:
        raise HTTPException(status_code=400, detail="action must be amend or cancel")
    try:
        uuid.UUID(order_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid order_id uuid") from exc

    new_notional = payload.get("new_notional")
    parsed_new_notional = None
    if action == "amend":
        if new_notional is None:
            raise HTTPException(status_code=400, detail="new_notional required for amend")
        parsed_new_notional = float(new_notional)
        if parsed_new_notional <= 0:
            raise HTTPException(status_code=400, detail="new_notional must be positive")

    with psycopg.connect(db_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO execution_command_log (
                  command_id, order_id, action, accepted, reason, payload, created_at
                ) VALUES (%s::uuid, %s::uuid, %s, TRUE, %s, %s::jsonb, now())
                """,
                (
                    str(uuid.uuid4()),
                    order_id,
                    action,
                    "control_panel_request",
                    json.dumps(
                        {
                            "source": "control_panel",
                            "new_notional": parsed_new_notional,
                            "justification": justification,
                        }
                    ),
                ),
            )

            if action == "cancel":
                cur.execute(
                    """
                    UPDATE execution_order_journal
                    SET
                      status = 'cancel_requested',
                      execution_metadata = execution_metadata || %s::jsonb,
                      state_version = state_version + 1,
                      updated_at = now()
                    WHERE order_id = %s::uuid
                    """,
                    (
                        json.dumps(
                            {
                                "control_panel_action": action,
                                "control_panel_user": session["user_id"],
                                "control_panel_justification": justification,
                            }
                        ),
                        order_id,
                    ),
                )
            else:
                cur.execute(
                    """
                    UPDATE execution_order_journal
                    SET
                      status = 'amend_requested',
                      execution_metadata = execution_metadata || %s::jsonb,
                      state_version = state_version + 1,
                      updated_at = now()
                    WHERE order_id = %s::uuid
                    """,
                    (
                        json.dumps(
                            {
                                "control_panel_action": action,
                                "control_panel_user": session["user_id"],
                                "control_panel_justification": justification,
                                "control_panel_new_notional": parsed_new_notional,
                            }
                        ),
                        order_id,
                    ),
                )

        audit_control_panel_action(
            conn,
            user_id=session["user_id"],
            role=session["role"],
            action=f"execution.{action}",
            section="execution",
            target=order_id,
            status="approved",
            reason=None,
            metadata={
                "justification": justification,
                "new_notional": parsed_new_notional,
            },
        )
        conn.commit()

    return {
        "status": "accepted",
        "order_id": order_id,
        "action": action,
        "new_notional": parsed_new_notional,
        "requested_by": session["user_id"],
    }


@app.get("/api/v1/control-panel/ops")
def control_panel_ops(
    x_control_panel_token: str | None = Header(default=None),
    row_limit: int = Query(default=30, ge=1, le=200),
) -> dict:
    session = get_operator_session(x_control_panel_token)
    metrics = {
        "alerts_open": 0,
        "alerts_critical": 0,
        "incidents_open": 0,
        "sla_breached_open_alerts": 0,
        "runbooks_24h": 0,
        "evidence_snapshots_24h": 0,
        "mttr_minutes_7d": 0.0,
    }
    alert_rows: list[dict] = []
    incident_rows: list[dict] = []
    runbook_rows: list[dict] = []
    mode = "online"
    try:
        with psycopg.connect(db_url()) as conn:
            ensure_control_panel_ops_tables(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                      COUNT(*) FILTER (WHERE status IN ('open', 'acknowledged')),
                      COUNT(*) FILTER (WHERE status IN ('open', 'acknowledged') AND severity = 'critical'),
                      COUNT(*) FILTER (WHERE status IN ('open', 'acknowledged') AND sla_due_at IS NOT NULL AND sla_due_at < now())
                    FROM control_panel_alert
                    """
                )
                row = cur.fetchone()
                metrics["alerts_open"] = int(row[0] or 0)
                metrics["alerts_critical"] = int(row[1] or 0)
                metrics["sla_breached_open_alerts"] = int(row[2] or 0)

                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM control_panel_incident
                    WHERE status IN ('open', 'investigating')
                    """
                )
                metrics["incidents_open"] = int(cur.fetchone()[0] or 0)

                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM control_panel_runbook_execution
                    WHERE created_at >= now() - interval '24 hours'
                    """
                )
                metrics["runbooks_24h"] = int(cur.fetchone()[0] or 0)
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM control_panel_reconciliation_evidence
                    WHERE captured_at >= now() - interval '24 hours'
                    """
                )
                metrics["evidence_snapshots_24h"] = int(cur.fetchone()[0] or 0)

                cur.execute(
                    """
                    SELECT COALESCE(AVG(EXTRACT(EPOCH FROM (resolved_at - opened_at)) / 60.0), 0.0)
                    FROM control_panel_incident
                    WHERE resolved_at IS NOT NULL
                      AND opened_at >= now() - interval '7 days'
                    """
                )
                metrics["mttr_minutes_7d"] = float(cur.fetchone()[0] or 0.0)

                cur.execute(
                    """
                    SELECT alert_id, source, severity, title, status, owner, sla_due_at, signal_ref, updated_at
                    FROM control_panel_alert
                    ORDER BY updated_at DESC
                    LIMIT %s
                    """,
                    (row_limit,),
                )
                for row in cur.fetchall():
                    alert_rows.append(
                        {
                            "alert_id": str(row[0]),
                            "source": str(row[1]),
                            "severity": str(row[2]),
                            "title": str(row[3]),
                            "status": str(row[4]),
                            "owner": row[5],
                            "sla_due_at": row[6].isoformat() if row[6] else None,
                            "signal_ref": row[7],
                            "updated_at": row[8].isoformat() if row[8] else None,
                        }
                    )

                cur.execute(
                    """
                    SELECT incident_id, alert_id, title, severity, status, owner, opened_at, resolved_at
                    FROM control_panel_incident
                    ORDER BY opened_at DESC
                    LIMIT %s
                    """,
                    (row_limit,),
                )
                for row in cur.fetchall():
                    incident_rows.append(
                        {
                            "incident_id": str(row[0]),
                            "alert_id": str(row[1]) if row[1] else None,
                            "title": str(row[2]),
                            "severity": str(row[3]),
                            "status": str(row[4]),
                            "owner": row[5],
                            "opened_at": row[6].isoformat() if row[6] else None,
                            "resolved_at": row[7].isoformat() if row[7] else None,
                        }
                    )

                cur.execute(
                    """
                    SELECT execution_id, incident_id, runbook_code, action, status, triggered_by, created_at, output
                    FROM control_panel_runbook_execution
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (row_limit,),
                )
                for row in cur.fetchall():
                    runbook_rows.append(
                        {
                            "execution_id": str(row[0]),
                            "incident_id": str(row[1]) if row[1] else None,
                            "runbook_code": str(row[2]),
                            "action": str(row[3]),
                            "status": str(row[4]),
                            "triggered_by": str(row[5]),
                            "created_at": row[6].isoformat() if row[6] else None,
                            "evidence_summary": (row[7] or {}).get("evidence_summary", {}) if isinstance(row[7], dict) else {},
                        }
                    )
    except Exception:
        mode = "degraded"

    return {
        "service": "control-panel",
        "module": "ops",
        "mode": mode,
        "session": session,
        "metrics": metrics,
        "alert_rows": alert_rows,
        "incident_rows": incident_rows,
        "runbook_rows": runbook_rows,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/v1/control-panel/ops/alerts/action")
def control_panel_ops_alert_action(
    payload: dict = Body(...),
    x_control_panel_token: str | None = Header(default=None),
) -> dict:
    session = get_operator_session(x_control_panel_token)
    require_min_role(session["role"], "operator")

    alert_id = str(payload.get("alert_id", "")).strip()
    action = str(payload.get("action", "")).strip().lower()
    owner = str(payload.get("owner", "")).strip() or session["user_id"]
    note = str(payload.get("note", "")).strip()
    justification = str(payload.get("justification", "")).strip()
    if len(justification) < 12:
        raise HTTPException(status_code=400, detail="justification must be at least 12 characters")
    if action not in {"acknowledge", "suppress", "resolve", "incident"}:
        raise HTTPException(status_code=400, detail="action must be acknowledge|suppress|resolve|incident")
    try:
        parsed_alert_id = str(uuid.UUID(alert_id))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid alert_id uuid") from exc

    incident_id = None
    with psycopg.connect(db_url()) as conn:
        ensure_control_panel_ops_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT title, severity, status
                FROM control_panel_alert
                WHERE alert_id = %s::uuid
                """,
                (parsed_alert_id,),
            )
            existing = cur.fetchone()
            if not existing:
                raise HTTPException(status_code=404, detail="alert not found")

            next_status = {
                "acknowledge": "acknowledged",
                "suppress": "suppressed",
                "resolve": "resolved",
                "incident": "acknowledged",
            }[action]
            cur.execute(
                """
                UPDATE control_panel_alert
                SET status = %s, owner = %s, updated_at = now(), details = details || %s::jsonb
                WHERE alert_id = %s::uuid
                """,
                (
                    next_status,
                    owner,
                    json.dumps({"control_panel_note": note, "last_action": action}),
                    parsed_alert_id,
                ),
            )
            if action == "incident":
                incident_id = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO control_panel_incident (
                      incident_id, alert_id, title, severity, status, owner, opened_at, timeline, notes
                    ) VALUES (%s::uuid, %s::uuid, %s, %s, 'open', %s, now(), %s::jsonb, %s)
                    """,
                    (
                        incident_id,
                        parsed_alert_id,
                        str(existing[0]),
                        str(existing[1]),
                        owner,
                        json.dumps(
                            [
                                {
                                    "ts": datetime.now(timezone.utc).isoformat(),
                                    "event": "incident_created_from_alert",
                                    "actor": session["user_id"],
                                }
                            ]
                        ),
                        note or "created from alert lifecycle action",
                    ),
                )

        audit_control_panel_action(
            conn,
            user_id=session["user_id"],
            role=session["role"],
            action=f"ops.alert.{action}",
            section="ops",
            target=parsed_alert_id,
            status="approved",
            reason=None,
            metadata={"owner": owner, "note": note, "justification": justification, "incident_id": incident_id},
        )
        conn.commit()

    return {
        "status": "accepted",
        "alert_id": parsed_alert_id,
        "action": action,
        "incident_id": incident_id,
        "owner": owner,
        "requested_by": session["user_id"],
    }


@app.post("/api/v1/control-panel/ops/alerts/ingest")
def control_panel_ops_alert_ingest(
    payload: dict = Body(...),
    x_control_panel_token: str | None = Header(default=None),
) -> dict:
    session = get_operator_session(x_control_panel_token)
    require_min_role(session["role"], "operator")
    source = str(payload.get("source", "")).strip().lower() or "manual"
    severity = str(payload.get("severity", "")).strip().lower() or "warning"
    title = str(payload.get("title", "")).strip()
    signal_ref = str(payload.get("signal_ref", "")).strip() or None
    sla_minutes = int(payload.get("sla_minutes", 30))
    if len(title) < 6:
        raise HTTPException(status_code=400, detail="title must be at least 6 characters")
    if severity not in {"info", "warning", "critical"}:
        raise HTTPException(status_code=400, detail="severity must be info|warning|critical")
    if sla_minutes < 1 or sla_minutes > 1440:
        raise HTTPException(status_code=400, detail="sla_minutes must be in [1, 1440]")
    alert_id = str(uuid.uuid4())
    with psycopg.connect(db_url()) as conn:
        ensure_control_panel_ops_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO control_panel_alert (
                  alert_id, source, severity, title, status, owner, sla_due_at, signal_ref, details
                ) VALUES (%s::uuid, %s, %s, %s, 'open', %s, now() + (%s || ' minutes')::interval, %s, %s::jsonb)
                """,
                (
                    alert_id,
                    source,
                    severity,
                    title,
                    session["user_id"],
                    str(sla_minutes),
                    signal_ref,
                    json.dumps({"ingest_mode": "control_panel_manual"}),
                ),
            )
        audit_control_panel_action(
            conn,
            user_id=session["user_id"],
            role=session["role"],
            action="ops.alert.ingest",
            section="ops",
            target=alert_id,
            status="approved",
            reason=None,
            metadata={"source": source, "severity": severity, "title": title, "signal_ref": signal_ref},
        )
        conn.commit()
    return {"status": "created", "alert_id": alert_id}


@app.post("/api/v1/control-panel/ops/runbook/execute")
def control_panel_ops_runbook_execute(
    payload: dict = Body(...),
    x_control_panel_token: str | None = Header(default=None),
) -> dict:
    session = get_operator_session(x_control_panel_token)
    require_min_role(session["role"], "operator")

    runbook_code = str(payload.get("runbook_code", "")).strip().upper()
    action = str(payload.get("action", "")).strip().lower() or "execute"
    incident_id_raw = str(payload.get("incident_id", "")).strip()
    order_id_raw = str(payload.get("order_id", "")).strip()
    correlation_id_raw = str(payload.get("correlation_id", "")).strip()
    lookback_minutes = int(payload.get("lookback_minutes", 120))
    justification = str(payload.get("justification", "")).strip()
    if len(runbook_code) < 4:
        raise HTTPException(status_code=400, detail="runbook_code is required")
    if len(justification) < 12:
        raise HTTPException(status_code=400, detail="justification must be at least 12 characters")
    incident_id = None
    order_id = None
    correlation_id = None
    if incident_id_raw:
        try:
            incident_id = str(uuid.UUID(incident_id_raw))
        except Exception as exc:
            raise HTTPException(status_code=400, detail="invalid incident_id uuid") from exc
    if order_id_raw:
        try:
            order_id = str(uuid.UUID(order_id_raw))
        except Exception as exc:
            raise HTTPException(status_code=400, detail="invalid order_id uuid") from exc
    if correlation_id_raw:
        try:
            correlation_id = str(uuid.UUID(correlation_id_raw))
        except Exception as exc:
            raise HTTPException(status_code=400, detail="invalid correlation_id uuid") from exc

    execution_id = str(uuid.uuid4())
    evidence_summary = {}
    with psycopg.connect(db_url()) as conn:
        ensure_control_panel_ops_tables(conn)
        evidence_summary = capture_runbook_reconciliation_evidence(
            conn=conn,
            execution_id=execution_id,
            incident_id=incident_id,
            order_id=order_id,
            correlation_id=correlation_id,
            lookback_minutes=lookback_minutes,
        )
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO control_panel_runbook_execution (
                  execution_id, incident_id, runbook_code, action, status, triggered_by, justification, output
                ) VALUES (%s::uuid, %s::uuid, %s, %s, 'completed', %s, %s, %s::jsonb)
                """,
                (
                    execution_id,
                    incident_id,
                    runbook_code,
                    action,
                    session["user_id"],
                    justification,
                    json.dumps(
                        {
                            "summary": "Runbook execution recorded by control panel baseline",
                            "operator_note": str(payload.get("operator_note", "")).strip(),
                            "linked_order_id": order_id,
                            "linked_correlation_id": correlation_id,
                            "evidence_summary": evidence_summary,
                        }
                    ),
                ),
            )
            if incident_id:
                cur.execute(
                    """
                    UPDATE control_panel_incident
                    SET timeline = timeline || %s::jsonb
                    WHERE incident_id = %s::uuid
                    """,
                    (
                        json.dumps(
                            [
                                {
                                    "ts": datetime.now(timezone.utc).isoformat(),
                                    "event": "runbook_executed",
                                    "runbook_code": runbook_code,
                                    "action": action,
                                    "actor": session["user_id"],
                                }
                            ]
                        ),
                        incident_id,
                    ),
                )

        audit_control_panel_action(
            conn,
            user_id=session["user_id"],
            role=session["role"],
            action="ops.runbook.execute",
            section="ops",
            target=incident_id,
            status="approved",
            reason=None,
            metadata={
                "execution_id": execution_id,
                "runbook_code": runbook_code,
                "action": action,
                "justification": justification,
                "order_id": order_id,
                "correlation_id": correlation_id,
                "evidence_summary": evidence_summary,
            },
        )
        conn.commit()

    return {
        "status": "completed",
        "execution_id": execution_id,
        "incident_id": incident_id,
        "runbook_code": runbook_code,
        "action": action,
        "triggered_by": session["user_id"],
        "evidence_summary": evidence_summary,
    }


@app.get("/api/v1/control-panel/research")
def control_panel_research(
    x_control_panel_token: str | None = Header(default=None),
    row_limit: int = Query(default=30, ge=1, le=200),
) -> dict:
    session = get_operator_session(x_control_panel_token)
    metrics = {
        "datasets_ready": 0,
        "backtests_24h": 0,
        "models_registered": 0,
        "promotion_ready_models": 0,
        "avg_readiness_score": 0.0,
        "best_sharpe_30d": 0.0,
    }
    dataset_rows: list[dict] = []
    backtest_rows: list[dict] = []
    model_rows: list[dict] = []
    mode = "online"
    try:
        with psycopg.connect(db_url()) as conn:
            ensure_research_seed_data(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                      COUNT(*) FILTER (WHERE status = 'ready'),
                      COUNT(*)
                    FROM control_panel_dataset_registry
                    """
                )
                row = cur.fetchone()
                metrics["datasets_ready"] = int(row[0] or 0)

                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM control_panel_backtest_run
                    WHERE created_at >= now() - interval '24 hours'
                    """
                )
                metrics["backtests_24h"] = int(cur.fetchone()[0] or 0)

                cur.execute(
                    """
                    SELECT
                      COUNT(*),
                      COUNT(*) FILTER (WHERE gate_status = 'ready'),
                      COALESCE(AVG(readiness_score), 0.0)
                    FROM control_panel_model_registry
                    """
                )
                row = cur.fetchone()
                metrics["models_registered"] = int(row[0] or 0)
                metrics["promotion_ready_models"] = int(row[1] or 0)
                metrics["avg_readiness_score"] = float(row[2] or 0.0)

                cur.execute(
                    """
                    SELECT COALESCE(MAX(sharpe), 0.0)
                    FROM control_panel_backtest_run
                    WHERE created_at >= now() - interval '30 days'
                    """
                )
                metrics["best_sharpe_30d"] = float(cur.fetchone()[0] or 0.0)

                cur.execute(
                    """
                    SELECT dataset_id, dataset_code, venue, symbol, timeframe, row_count, start_ts, end_ts, status, lineage_ref, updated_at
                    FROM control_panel_dataset_registry
                    ORDER BY updated_at DESC
                    LIMIT %s
                    """,
                    (row_limit,),
                )
                for row in cur.fetchall():
                    dataset_rows.append(
                        {
                            "dataset_id": str(row[0]),
                            "dataset_code": str(row[1]),
                            "venue": str(row[2]),
                            "symbol": str(row[3]),
                            "timeframe": str(row[4]),
                            "row_count": int(row[5] or 0),
                            "start_ts": row[6].isoformat() if row[6] else None,
                            "end_ts": row[7].isoformat() if row[7] else None,
                            "status": str(row[8]),
                            "lineage_ref": row[9],
                            "updated_at": row[10].isoformat() if row[10] else None,
                        }
                    )

                cur.execute(
                    """
                    SELECT run_id, dataset_id, strategy_code, model_version, status, pnl, sharpe, max_drawdown_pct, created_at, completed_at
                    FROM control_panel_backtest_run
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (row_limit,),
                )
                for row in cur.fetchall():
                    backtest_rows.append(
                        {
                            "run_id": str(row[0]),
                            "dataset_id": str(row[1]) if row[1] else None,
                            "strategy_code": str(row[2]),
                            "model_version": row[3],
                            "status": str(row[4]),
                            "pnl": float(row[5] or 0.0),
                            "sharpe": float(row[6] or 0.0),
                            "max_drawdown_pct": float(row[7] or 0.0),
                            "created_at": row[8].isoformat() if row[8] else None,
                            "completed_at": row[9].isoformat() if row[9] else None,
                        }
                    )

                cur.execute(
                    """
                    SELECT model_id, model_name, model_version, experiment_ref, stage, readiness_score, gate_status, updated_at
                    FROM control_panel_model_registry
                    ORDER BY updated_at DESC
                    LIMIT %s
                    """,
                    (row_limit,),
                )
                for row in cur.fetchall():
                    model_rows.append(
                        {
                            "model_id": str(row[0]),
                            "model_name": str(row[1]),
                            "model_version": str(row[2]),
                            "experiment_ref": row[3],
                            "stage": str(row[4]),
                            "readiness_score": float(row[5] or 0.0),
                            "gate_status": str(row[6]),
                            "updated_at": row[7].isoformat() if row[7] else None,
                        }
                    )
    except Exception:
        mode = "degraded"

    return {
        "service": "control-panel",
        "module": "research",
        "mode": mode,
        "session": session,
        "metrics": metrics,
        "dataset_rows": dataset_rows,
        "backtest_rows": backtest_rows,
        "model_rows": model_rows,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/v1/control-panel/research/backtest")
def control_panel_research_backtest(
    payload: dict = Body(...),
    x_control_panel_token: str | None = Header(default=None),
) -> dict:
    session = get_operator_session(x_control_panel_token)
    require_min_role(session["role"], "operator")
    dataset_id = str(payload.get("dataset_id", "")).strip()
    strategy_code = str(payload.get("strategy_code", "")).strip().upper()
    model_version = str(payload.get("model_version", "")).strip() or None
    justification = str(payload.get("justification", "")).strip()
    if len(justification) < 12:
        raise HTTPException(status_code=400, detail="justification must be at least 12 characters")
    if len(strategy_code) < 3:
        raise HTTPException(status_code=400, detail="strategy_code required")
    try:
        parsed_dataset_id = str(uuid.UUID(dataset_id))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid dataset_id uuid") from exc

    run_id = str(uuid.uuid4())
    with psycopg.connect(db_url()) as conn:
        ensure_control_panel_research_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM control_panel_dataset_registry WHERE dataset_id = %s::uuid",
                (parsed_dataset_id,),
            )
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="dataset not found")
            cur.execute(
                """
                INSERT INTO control_panel_backtest_run (
                  run_id, dataset_id, strategy_code, model_version, status, pnl, sharpe, max_drawdown_pct, params, triggered_by, completed_at
                ) VALUES (%s::uuid, %s::uuid, %s, %s, 'completed', 0, 0, 0, %s::jsonb, %s, now())
                """,
                (
                    run_id,
                    parsed_dataset_id,
                    strategy_code,
                    model_version,
                    json.dumps({"mode": "baseline", "source": "control_panel"}),
                    session["user_id"],
                ),
            )
        audit_control_panel_action(
            conn,
            user_id=session["user_id"],
            role=session["role"],
            action="research.backtest.launch",
            section="research",
            target=run_id,
            status="approved",
            reason=None,
            metadata={"dataset_id": parsed_dataset_id, "strategy_code": strategy_code, "model_version": model_version, "justification": justification},
        )
        conn.commit()
    return {"status": "accepted", "run_id": run_id, "strategy_code": strategy_code, "dataset_id": parsed_dataset_id}


@app.post("/api/v1/control-panel/research/model/promote")
def control_panel_research_model_promote(
    payload: dict = Body(...),
    x_control_panel_token: str | None = Header(default=None),
) -> dict:
    session = get_operator_session(x_control_panel_token)
    require_min_role(session["role"], "risk_manager")
    model_name = str(payload.get("model_name", "")).strip()
    model_version = str(payload.get("model_version", "")).strip()
    stage = str(payload.get("stage", "")).strip().lower() or "staging"
    readiness_score = float(payload.get("readiness_score", 0.0))
    gate_status = str(payload.get("gate_status", "")).strip().lower() or "pending"
    justification = str(payload.get("justification", "")).strip()
    if len(justification) < 12:
        raise HTTPException(status_code=400, detail="justification must be at least 12 characters")
    if not model_name or not model_version:
        raise HTTPException(status_code=400, detail="model_name and model_version required")
    if stage not in {"candidate", "staging", "production", "archived"}:
        raise HTTPException(status_code=400, detail="invalid stage")
    if gate_status not in {"pending", "ready", "rejected"}:
        raise HTTPException(status_code=400, detail="invalid gate_status")
    if readiness_score < 0.0 or readiness_score > 1.0:
        raise HTTPException(status_code=400, detail="readiness_score must be in [0, 1]")

    model_id = str(uuid.uuid4())
    with psycopg.connect(db_url()) as conn:
        ensure_control_panel_research_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO control_panel_model_registry (
                  model_id, model_name, model_version, experiment_ref, stage, readiness_score, gate_status, metrics, updated_at
                )
                VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, %s::jsonb, now())
                ON CONFLICT (model_name, model_version)
                DO UPDATE SET
                  stage = EXCLUDED.stage,
                  readiness_score = EXCLUDED.readiness_score,
                  gate_status = EXCLUDED.gate_status,
                  metrics = EXCLUDED.metrics,
                  updated_at = now()
                RETURNING model_id
                """,
                (
                    model_id,
                    model_name,
                    model_version,
                    str(payload.get("experiment_ref", "")).strip() or None,
                    stage,
                    readiness_score,
                    gate_status,
                    json.dumps(payload.get("metrics", {})),
                ),
            )
            model_id = str(cur.fetchone()[0])
        audit_control_panel_action(
            conn,
            user_id=session["user_id"],
            role=session["role"],
            action="research.model.promote",
            section="research",
            target=model_id,
            status="approved",
            reason=None,
            metadata={
                "model_name": model_name,
                "model_version": model_version,
                "stage": stage,
                "gate_status": gate_status,
                "readiness_score": readiness_score,
                "justification": justification,
            },
        )
        conn.commit()
    return {"status": "updated", "model_id": model_id, "model_name": model_name, "model_version": model_version, "stage": stage, "gate_status": gate_status}


@app.get("/api/v1/control-panel/config")
def control_panel_config(
    x_control_panel_token: str | None = Header(default=None),
    environment: str = Query(default="dev", min_length=3, max_length=16),
    row_limit: int = Query(default=40, ge=1, le=200),
) -> dict:
    session = get_operator_session(x_control_panel_token)
    env_name = environment.strip().lower()
    if env_name not in {"dev", "paper", "prod"}:
        raise HTTPException(status_code=400, detail="environment must be dev|paper|prod")
    metrics = {
        "keys_total": 0,
        "high_risk_keys": 0,
        "pending_changes": 0,
        "applied_24h": 0,
        "rollbacks_7d": 0,
        "drift_keys": 0,
    }
    config_rows: list[dict] = []
    change_rows: list[dict] = []
    history_rows: list[dict] = []
    mode = "online"
    try:
        with psycopg.connect(db_url()) as conn:
            ensure_config_seed_data(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                      COUNT(*) FILTER (WHERE environment = %s),
                      COUNT(*) FILTER (WHERE environment = %s AND risk_level = 'high')
                    FROM control_panel_config_registry
                    """,
                    (env_name, env_name),
                )
                row = cur.fetchone()
                metrics["keys_total"] = int(row[0] or 0)
                metrics["high_risk_keys"] = int(row[1] or 0)

                cur.execute("SELECT COUNT(*) FROM control_panel_config_change_request WHERE status = 'pending'")
                metrics["pending_changes"] = int(cur.fetchone()[0] or 0)
                cur.execute("SELECT COUNT(*) FROM control_panel_config_change_request WHERE status = 'applied' AND decided_at >= now() - interval '24 hours'")
                metrics["applied_24h"] = int(cur.fetchone()[0] or 0)
                cur.execute("SELECT COUNT(*) FROM control_panel_config_change_history WHERE action = 'rollback' AND created_at >= now() - interval '7 days'")
                metrics["rollbacks_7d"] = int(cur.fetchone()[0] or 0)
                cur.execute(
                    """
                    SELECT COUNT(*) FROM (
                      SELECT config_key, COUNT(DISTINCT config_value::text) AS variants
                      FROM control_panel_config_registry
                      GROUP BY config_key
                      HAVING COUNT(DISTINCT config_value::text) > 1
                    ) d
                    """
                )
                metrics["drift_keys"] = int(cur.fetchone()[0] or 0)

                cur.execute(
                    """
                    SELECT config_key, environment, config_value, value_type, risk_level, min_role, schema_ref, updated_by, updated_at
                    FROM control_panel_config_registry
                    WHERE environment = %s
                    ORDER BY config_key ASC
                    LIMIT %s
                    """,
                    (env_name, row_limit),
                )
                for row in cur.fetchall():
                    config_rows.append(
                        {
                            "config_key": str(row[0]),
                            "environment": str(row[1]),
                            "config_value": row[2],
                            "value_type": str(row[3]),
                            "risk_level": str(row[4]),
                            "min_role": str(row[5]),
                            "schema_ref": row[6],
                            "updated_by": str(row[7]),
                            "updated_at": row[8].isoformat() if row[8] else None,
                        }
                    )

                cur.execute(
                    """
                    SELECT change_id, config_key, environment, status, requested_by, approved_by, created_at, decided_at
                    FROM control_panel_config_change_request
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (row_limit,),
                )
                for row in cur.fetchall():
                    change_rows.append(
                        {
                            "change_id": str(row[0]),
                            "config_key": str(row[1]),
                            "environment": str(row[2]),
                            "status": str(row[3]),
                            "requested_by": str(row[4]),
                            "approved_by": row[5],
                            "created_at": row[6].isoformat() if row[6] else None,
                            "decided_at": row[7].isoformat() if row[7] else None,
                        }
                    )

                cur.execute(
                    """
                    SELECT history_id, change_id, action, actor, metadata, created_at
                    FROM control_panel_config_change_history
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (row_limit,),
                )
                for row in cur.fetchall():
                    history_rows.append(
                        {
                            "history_id": str(row[0]),
                            "change_id": str(row[1]),
                            "action": str(row[2]),
                            "actor": str(row[3]),
                            "metadata": row[4],
                            "created_at": row[5].isoformat() if row[5] else None,
                        }
                    )
    except Exception:
        mode = "degraded"

    return {
        "service": "control-panel",
        "module": "config-governance",
        "mode": mode,
        "session": session,
        "environment": env_name,
        "metrics": metrics,
        "config_rows": config_rows,
        "change_rows": change_rows,
        "history_rows": history_rows,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/v1/control-panel/config/propose")
def control_panel_config_propose(
    payload: dict = Body(...),
    x_control_panel_token: str | None = Header(default=None),
) -> dict:
    session = get_operator_session(x_control_panel_token)
    require_min_role(session["role"], "operator")
    config_key = str(payload.get("config_key", "")).strip()
    env_name = str(payload.get("environment", "dev")).strip().lower()
    justification = str(payload.get("justification", "")).strip()
    proposed_value = payload.get("proposed_value")
    if len(justification) < 12:
        raise HTTPException(status_code=400, detail="justification must be at least 12 characters")
    if env_name not in {"dev", "paper", "prod"}:
        raise HTTPException(status_code=400, detail="environment must be dev|paper|prod")
    if not config_key:
        raise HTTPException(status_code=400, detail="config_key required")

    change_id = str(uuid.uuid4())
    status = "pending"
    with psycopg.connect(db_url()) as conn:
        ensure_config_seed_data(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT config_value, value_type, min_role, risk_level
                FROM control_panel_config_registry
                WHERE config_key = %s AND environment = %s
                LIMIT 1
                """,
                (config_key, env_name),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="config_key/environment pair not found")
            previous_value, value_type, min_role, risk_level = row[0], str(row[1]), str(row[2]), str(row[3])
            if not validate_typed_config(value_type, proposed_value):
                raise HTTPException(status_code=400, detail=f"proposed_value must match type {value_type}")
            require_min_role(session["role"], min_role)
            if risk_level == "low":
                status = "approved"
            cur.execute(
                """
                INSERT INTO control_panel_config_change_request (
                  change_id, config_key, environment, proposed_value, previous_value, status, requested_by, justification
                ) VALUES (%s::uuid, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s)
                """,
                (
                    change_id,
                    config_key,
                    env_name,
                    json.dumps(proposed_value),
                    json.dumps(previous_value),
                    status,
                    session["user_id"],
                    justification,
                ),
            )
            cur.execute(
                """
                INSERT INTO control_panel_config_change_history (history_id, change_id, action, actor, metadata)
                VALUES (%s::uuid, %s::uuid, 'proposed', %s, %s::jsonb)
                """,
                (str(uuid.uuid4()), change_id, session["user_id"], json.dumps({"status": status, "risk_level": risk_level})),
            )
        audit_control_panel_action(
            conn,
            user_id=session["user_id"],
            role=session["role"],
            action="config.propose",
            section="config",
            target=change_id,
            status="approved",
            reason=None,
            metadata={"config_key": config_key, "environment": env_name, "justification": justification, "status": status},
        )
        conn.commit()
    return {"status": status, "change_id": change_id, "config_key": config_key, "environment": env_name}


@app.post("/api/v1/control-panel/config/approve")
def control_panel_config_approve(
    payload: dict = Body(...),
    x_control_panel_token: str | None = Header(default=None),
) -> dict:
    session = get_operator_session(x_control_panel_token)
    require_min_role(session["role"], "admin")
    change_id = str(payload.get("change_id", "")).strip()
    justification = str(payload.get("justification", "")).strip()
    if len(justification) < 12:
        raise HTTPException(status_code=400, detail="justification must be at least 12 characters")
    try:
        parsed_change_id = str(uuid.UUID(change_id))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid change_id uuid") from exc
    with psycopg.connect(db_url()) as conn:
        ensure_control_panel_config_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE control_panel_config_change_request
                SET status = 'approved', approved_by = %s, decided_at = now()
                WHERE change_id = %s::uuid AND status = 'pending'
                """,
                (session["user_id"], parsed_change_id),
            )
            if int(cur.rowcount or 0) == 0:
                raise HTTPException(status_code=409, detail="change is not pending or not found")
            cur.execute(
                "INSERT INTO control_panel_config_change_history (history_id, change_id, action, actor, metadata) VALUES (%s::uuid, %s::uuid, 'approved', %s, %s::jsonb)",
                (str(uuid.uuid4()), parsed_change_id, session["user_id"], json.dumps({"justification": justification})),
            )
        audit_control_panel_action(
            conn,
            user_id=session["user_id"],
            role=session["role"],
            action="config.approve",
            section="config",
            target=parsed_change_id,
            status="approved",
            reason=None,
            metadata={"justification": justification},
        )
        conn.commit()
    return {"status": "approved", "change_id": parsed_change_id}


@app.post("/api/v1/control-panel/config/apply")
def control_panel_config_apply(
    payload: dict = Body(...),
    x_control_panel_token: str | None = Header(default=None),
) -> dict:
    session = get_operator_session(x_control_panel_token)
    require_min_role(session["role"], "risk_manager")
    change_id = str(payload.get("change_id", "")).strip()
    justification = str(payload.get("justification", "")).strip()
    if len(justification) < 12:
        raise HTTPException(status_code=400, detail="justification must be at least 12 characters")
    try:
        parsed_change_id = str(uuid.UUID(change_id))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid change_id uuid") from exc

    with psycopg.connect(db_url()) as conn:
        ensure_control_panel_config_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT config_key, environment, proposed_value, status
                FROM control_panel_config_change_request
                WHERE change_id = %s::uuid
                LIMIT 1
                """,
                (parsed_change_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="change not found")
            config_key, env_name, proposed_value, status = str(row[0]), str(row[1]), row[2], str(row[3])
            if status not in {"approved"}:
                raise HTTPException(status_code=409, detail="change must be approved before apply")
            cur.execute(
                """
                UPDATE control_panel_config_registry
                SET config_value = %s::jsonb, updated_by = %s, updated_at = now()
                WHERE config_key = %s AND environment = %s
                """,
                (json.dumps(proposed_value), session["user_id"], config_key, env_name),
            )
            cur.execute(
                """
                UPDATE control_panel_config_change_request
                SET status = 'applied', decided_at = now()
                WHERE change_id = %s::uuid
                """,
                (parsed_change_id,),
            )
            cur.execute(
                "INSERT INTO control_panel_config_change_history (history_id, change_id, action, actor, metadata) VALUES (%s::uuid, %s::uuid, 'applied', %s, %s::jsonb)",
                (str(uuid.uuid4()), parsed_change_id, session["user_id"], json.dumps({"justification": justification})),
            )
        audit_control_panel_action(
            conn,
            user_id=session["user_id"],
            role=session["role"],
            action="config.apply",
            section="config",
            target=parsed_change_id,
            status="approved",
            reason=None,
            metadata={"justification": justification},
        )
        conn.commit()
    return {"status": "applied", "change_id": parsed_change_id}


@app.post("/api/v1/control-panel/config/rollback")
def control_panel_config_rollback(
    payload: dict = Body(...),
    x_control_panel_token: str | None = Header(default=None),
) -> dict:
    session = get_operator_session(x_control_panel_token)
    require_min_role(session["role"], "admin")
    change_id = str(payload.get("change_id", "")).strip()
    justification = str(payload.get("justification", "")).strip()
    if len(justification) < 12:
        raise HTTPException(status_code=400, detail="justification must be at least 12 characters")
    try:
        parsed_change_id = str(uuid.UUID(change_id))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid change_id uuid") from exc

    with psycopg.connect(db_url()) as conn:
        ensure_control_panel_config_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT config_key, environment, previous_value
                FROM control_panel_config_change_request
                WHERE change_id = %s::uuid
                LIMIT 1
                """,
                (parsed_change_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="change not found")
            config_key, env_name, previous_value = str(row[0]), str(row[1]), row[2]
            cur.execute(
                """
                UPDATE control_panel_config_registry
                SET config_value = %s::jsonb, updated_by = %s, updated_at = now()
                WHERE config_key = %s AND environment = %s
                """,
                (json.dumps(previous_value), session["user_id"], config_key, env_name),
            )
            rollback_change_id = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO control_panel_config_change_request (
                  change_id, config_key, environment, proposed_value, previous_value, status, requested_by, approved_by, justification, decided_at
                ) VALUES (%s::uuid, %s, %s, %s::jsonb, %s::jsonb, 'applied', %s, %s, %s, now())
                """,
                (
                    rollback_change_id,
                    config_key,
                    env_name,
                    json.dumps(previous_value),
                    json.dumps(previous_value),
                    session["user_id"],
                    session["user_id"],
                    f"rollback:{parsed_change_id}:{justification}",
                ),
            )
            cur.execute(
                "INSERT INTO control_panel_config_change_history (history_id, change_id, action, actor, metadata) VALUES (%s::uuid, %s::uuid, 'rollback', %s, %s::jsonb)",
                (str(uuid.uuid4()), rollback_change_id, session["user_id"], json.dumps({"rollback_of": parsed_change_id, "justification": justification})),
            )
        audit_control_panel_action(
            conn,
            user_id=session["user_id"],
            role=session["role"],
            action="config.rollback",
            section="config",
            target=parsed_change_id,
            status="approved",
            reason=None,
            metadata={"justification": justification},
        )
        conn.commit()
    return {"status": "rolled_back", "rollback_of": parsed_change_id}


@app.get("/api/v1/control-panel/search")
def control_panel_search(
    q: str = Query(min_length=1, max_length=64),
    x_control_panel_token: str | None = Header(default=None),
) -> dict:
    session = get_operator_session(x_control_panel_token)
    term = q.strip().lower()
    rows: list[dict] = []
    if len(term) < 2:
        return {"service": "control-panel", "module": "search", "session": session, "results": rows}
    try:
        with psycopg.connect(db_url()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT venue, symbol
                    FROM venue_market
                    WHERE lower(venue) LIKE %s OR lower(symbol) LIKE %s
                    ORDER BY venue, symbol
                    LIMIT 8
                    """,
                    (f"%{term}%", f"%{term}%"),
                )
                for venue, symbol in cur.fetchall():
                    rows.append({"type": "market", "label": f"{venue}:{symbol}", "section": "charting"})

                cur.execute(
                    """
                    SELECT config_key, environment
                    FROM control_panel_config_registry
                    WHERE lower(config_key) LIKE %s
                    ORDER BY config_key, environment
                    LIMIT 8
                    """,
                    (f"%{term}%",),
                )
                for config_key, environment in cur.fetchall():
                    rows.append({"type": "config", "label": f"{config_key} [{environment}]", "section": "config"})

                cur.execute(
                    """
                    SELECT model_name, model_version, stage
                    FROM control_panel_model_registry
                    WHERE lower(model_name) LIKE %s OR lower(model_version) LIKE %s
                    ORDER BY updated_at DESC
                    LIMIT 8
                    """,
                    (f"%{term}%", f"%{term}%"),
                )
                for model_name, model_version, stage in cur.fetchall():
                    rows.append(
                        {
                            "type": "model",
                            "label": f"{model_name}:{model_version} ({stage})",
                            "section": "research",
                        }
                    )
        if (
            "kpi" in term
            or "coverage" in term
            or "ohlcv" in term
            or "tick" in term
            or "latency" in term
        ):
            rows.append(
                {
                    "type": "kpi",
                    "label": "Ingestion KPI Monitor",
                    "section": "kpi",
                }
            )
    except Exception:
        rows = []
    return {
        "service": "control-panel",
        "module": "search",
        "session": session,
        "results": rows[:20],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/v1/control-panel/charting/profile")
def control_panel_charting_profile(
    venue: str = Query(min_length=1, max_length=64),
    symbol: str = Query(min_length=1, max_length=64),
    timeframe: str = Query(default="1m", min_length=1, max_length=16),
    x_control_panel_token: str | None = Header(default=None),
) -> dict:
    session = get_operator_session(x_control_panel_token)
    venue_norm = normalize_venue(venue)
    symbol_norm = normalize_symbol(symbol)
    tf = timeframe.strip().lower()

    profile = {
        "venue": venue_norm,
        "symbol": symbol_norm,
        "timeframe": tf,
        "asset_class": "unknown",
        "ingest_enabled": None,
        "market_enabled": None,
        "latest_bar": None,
        "latest_risk_state": None,
        "latest_execution_state": None,
        "open_gap_count": 0,
    }

    with psycopg.connect(db_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT asset_class, enabled, ingest_enabled
                FROM venue_market
                WHERE venue = %s AND symbol = %s
                LIMIT 1
                """,
                (venue_norm, symbol_norm),
            )
            row = cur.fetchone()
            if row:
                profile["asset_class"] = str(row[0])
                profile["market_enabled"] = bool(row[1])
                profile["ingest_enabled"] = bool(row[2])

            cur.execute(
                """
                SELECT bucket_start, open, high, low, close, volume, trade_count
                FROM ohlcv_bar
                WHERE venue = %s AND canonical_symbol = %s AND timeframe = %s
                ORDER BY bucket_start DESC
                LIMIT 1
                """,
                (venue_norm, symbol_norm, tf),
            )
            row = cur.fetchone()
            if row:
                profile["latest_bar"] = {
                    "bucket_start": row[0].isoformat() if row[0] else None,
                    "open": float(row[1] or 0.0),
                    "high": float(row[2] or 0.0),
                    "low": float(row[3] or 0.0),
                    "close": float(row[4] or 0.0),
                    "volume": float(row[5] or 0.0),
                    "trade_count": int(row[6] or 0),
                }

            cur.execute(
                """
                SELECT current_exposure_notional, drawdown_pct, kill_switch_enabled, updated_at
                FROM risk_state
                WHERE venue = %s AND canonical_symbol = %s AND timeframe = %s
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (venue_norm, symbol_norm, tf),
            )
            row = cur.fetchone()
            if row:
                profile["latest_risk_state"] = {
                    "exposure_notional": float(row[0] or 0.0),
                    "drawdown_pct": float(row[1] or 0.0),
                    "kill_switch_enabled": bool(row[2]),
                    "updated_at": row[3].isoformat() if row[3] else None,
                }

            cur.execute(
                """
                SELECT order_id, status, side, requested_notional, updated_at
                FROM execution_order_journal
                WHERE venue = %s AND canonical_symbol = %s AND timeframe = %s
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (venue_norm, symbol_norm, tf),
            )
            row = cur.fetchone()
            if row:
                profile["latest_execution_state"] = {
                    "order_id": str(row[0]),
                    "status": str(row[1]),
                    "side": str(row[2]),
                    "requested_notional": float(row[3] or 0.0),
                    "updated_at": row[4].isoformat() if row[4] else None,
                }

            cur.execute(
                """
                SELECT COUNT(*)
                FROM gap_log
                WHERE venue = %s
                  AND canonical_symbol = %s
                  AND status IN ('open', 'backfill_queued')
                """,
                (venue_norm, symbol_norm),
            )
            profile["open_gap_count"] = int(cur.fetchone()[0] or 0)

    return {
        "service": "control-panel",
        "module": "charting-workbench",
        "session": session,
        "profile": profile,
        "links": {
            "full_chart": f"/charting?venue={urllib.parse.quote(venue_norm)}&symbol={urllib.parse.quote(symbol_norm)}&timeframe={urllib.parse.quote(tf)}",
            "bars_history_api": f"/api/v1/bars/history?venue={urllib.parse.quote(venue_norm)}&symbol={urllib.parse.quote(symbol_norm)}&timeframe={urllib.parse.quote(tf)}&limit=500",
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


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


def coinbase_product_candidates(symbol: str) -> list[str]:
    symbol_norm = symbol.strip().upper()
    candidates: list[str] = []
    primary = coinbase_product(symbol_norm)
    if primary:
        candidates.append(primary)

    if symbol_norm.endswith("USD") and len(symbol_norm) >= 6:
        base = symbol_norm[:-3]
        candidates.append(f"{base}-USDC")
        candidates.append(f"{base}-USD")
    elif symbol_norm.endswith("USDC") and len(symbol_norm) >= 7:
        base = symbol_norm[:-4]
        candidates.append(f"{base}-USD")

    dedup: list[str] = []
    for candidate in candidates:
        normalized = candidate.strip().upper()
        if normalized and normalized not in dedup:
            dedup.append(normalized)
    return dedup


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
                "max": "240",
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
    for product in coinbase_product_candidates(symbol):
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
            if exc.code not in {400, 403, 429, 500, 503}:
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
        try:
            with urllib.request.urlopen(v3_req, timeout=VENUE_FETCH_TIMEOUT_SECS) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in {400, 404}:
                continue
            raise

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
        if bars:
            return bars
    return []


def fetch_from_venue(venue: str, symbol: str, ranges: list[tuple[datetime, datetime]]) -> tuple[int, str]:
    # Keep each venue request within provider limits (Coinbase candles API is strict: max 300).
    chunk_minutes_map = {
        "oanda": 4500,
        "coinbase": 300,
        "capital": 240,
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
                if venue == "capital" and "error.invalid.max.daterange" in body:
                    fallback_end = min(
                        chunk_end,
                        chunk_start + timedelta(minutes=239),
                    )
                    if fallback_end > chunk_start:
                        try:
                            bars = fetch_capital_range(symbol, chunk_start, fallback_end)
                            if bars:
                                with psycopg.connect(db_url()) as conn:
                                    upsert_bars(conn, venue, symbol, bars)
                                    conn.commit()
                                fetched += len(bars)
                                failed_calls = 0
                                continue
                        except Exception:
                            pass
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
