from fastapi import APIRouter, Request, Response

from app.services.control_panel.legacy_proxy import proxy_to_legacy

router = APIRouter()


@router.get("/api/v1/control-panel/execution")
async def control_panel_execution(request: Request) -> Response:
    return await proxy_to_legacy(request)


@router.post("/api/v1/control-panel/execution/command")
async def control_panel_execution_command(request: Request) -> Response:
    return await proxy_to_legacy(request)
