from fastapi import APIRouter, Request, Response

from app.services.control_panel.legacy_proxy import proxy_to_legacy

router = APIRouter()


@router.get("/api/v1/control-panel/ops")
async def control_panel_ops(request: Request) -> Response:
    return await proxy_to_legacy(request)


@router.post("/api/v1/control-panel/ops/alerts/action")
async def control_panel_ops_alert_action(request: Request) -> Response:
    return await proxy_to_legacy(request)


@router.post("/api/v1/control-panel/ops/alerts/ingest")
async def control_panel_ops_alert_ingest(request: Request) -> Response:
    return await proxy_to_legacy(request)


@router.post("/api/v1/control-panel/ops/runbook/execute")
async def control_panel_ops_runbook_execute(request: Request) -> Response:
    return await proxy_to_legacy(request)
