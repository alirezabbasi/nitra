from fastapi import APIRouter, Request, Response

from app.services.control_panel.legacy_proxy import proxy_to_legacy

router = APIRouter()


@router.get("/api/v1/control-panel/config")
async def control_panel_config(request: Request) -> Response:
    return await proxy_to_legacy(request)


@router.post("/api/v1/control-panel/config/propose")
async def control_panel_config_propose(request: Request) -> Response:
    return await proxy_to_legacy(request)


@router.post("/api/v1/control-panel/config/approve")
async def control_panel_config_approve(request: Request) -> Response:
    return await proxy_to_legacy(request)


@router.post("/api/v1/control-panel/config/apply")
async def control_panel_config_apply(request: Request) -> Response:
    return await proxy_to_legacy(request)


@router.post("/api/v1/control-panel/config/rollback")
async def control_panel_config_rollback(request: Request) -> Response:
    return await proxy_to_legacy(request)
