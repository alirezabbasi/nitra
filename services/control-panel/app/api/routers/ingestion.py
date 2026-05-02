from fastapi import APIRouter, Request, Response

from app.services.control_panel.legacy_proxy import proxy_to_legacy

router = APIRouter()


@router.get("/api/v1/control-panel/ingestion")
async def control_panel_ingestion(request: Request) -> Response:
    return await proxy_to_legacy(request)


@router.get("/api/v1/control-panel/ingestion/kpi")
async def control_panel_ingestion_kpi(request: Request) -> Response:
    return await proxy_to_legacy(request)


@router.post("/api/v1/control-panel/ingestion/backfill-window")
async def control_panel_ingestion_backfill_window(request: Request) -> Response:
    return await proxy_to_legacy(request)


@router.post("/api/v1/control-panel/ingestion/failover-policy")
async def control_panel_ingestion_failover_policy(request: Request) -> Response:
    return await proxy_to_legacy(request)


@router.post("/api/v1/control-panel/ingestion/session-policy")
async def control_panel_ingestion_session_policy(request: Request) -> Response:
    return await proxy_to_legacy(request)


@router.post("/api/v1/control-panel/ingestion/ws-policy")
async def control_panel_ingestion_ws_policy(request: Request) -> Response:
    return await proxy_to_legacy(request)


@router.post("/api/v1/control-panel/ingestion/rate-limit-policy")
async def control_panel_ingestion_rate_limit_policy(request: Request) -> Response:
    return await proxy_to_legacy(request)


@router.post("/api/v1/control-panel/ingestion/kafka-topic-policy")
async def control_panel_ingestion_kafka_topic_policy(request: Request) -> Response:
    return await proxy_to_legacy(request)


@router.post("/api/v1/control-panel/ingestion/kafka-lag-recovery")
async def control_panel_ingestion_kafka_lag_recovery(request: Request) -> Response:
    return await proxy_to_legacy(request)


@router.post("/api/v1/control-panel/ingestion/kafka-dead-letter-replay")
async def control_panel_ingestion_kafka_dead_letter_replay(request: Request) -> Response:
    return await proxy_to_legacy(request)


@router.post("/api/v1/control-panel/ingestion/raw-lake/replay-manifest")
async def control_panel_ingestion_raw_lake_replay_manifest(request: Request) -> Response:
    return await proxy_to_legacy(request)


@router.post("/api/v1/control-panel/ingestion/raw-lake/retention-policy")
async def control_panel_ingestion_raw_lake_retention_policy(request: Request) -> Response:
    return await proxy_to_legacy(request)


@router.post("/api/v1/control-panel/ingestion/raw-lake/restore-drill")
async def control_panel_ingestion_raw_lake_restore_drill(request: Request) -> Response:
    return await proxy_to_legacy(request)
