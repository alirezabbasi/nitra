from fastapi import APIRouter, Request, Response

from app.services.control_panel.legacy_proxy import proxy_to_legacy

router = APIRouter()


@router.get("/api/v1/control-panel/risk-portfolio")
async def control_panel_risk_portfolio(request: Request) -> Response:
    return await proxy_to_legacy(request)


@router.post("/api/v1/control-panel/risk-limits")
async def control_panel_risk_limits_update(request: Request) -> Response:
    return await proxy_to_legacy(request)


@router.post("/api/v1/control-panel/risk/kill-switch")
async def control_panel_risk_kill_switch(request: Request) -> Response:
    return await proxy_to_legacy(request)
