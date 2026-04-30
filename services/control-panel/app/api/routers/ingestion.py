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
