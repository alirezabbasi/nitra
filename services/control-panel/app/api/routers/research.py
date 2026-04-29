from fastapi import APIRouter, Request, Response

from app.services.control_panel.legacy_proxy import proxy_to_legacy

router = APIRouter()


@router.get("/api/v1/control-panel/research")
async def control_panel_research(request: Request) -> Response:
    return await proxy_to_legacy(request)


@router.post("/api/v1/control-panel/research/backtest")
async def control_panel_research_backtest(request: Request) -> Response:
    return await proxy_to_legacy(request)


@router.post("/api/v1/control-panel/research/model/promote")
async def control_panel_research_model_promote(request: Request) -> Response:
    return await proxy_to_legacy(request)
