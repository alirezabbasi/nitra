from fastapi import APIRouter, Request, Response

from app.services.control_panel.legacy_proxy import proxy_to_legacy

router = APIRouter()


@router.get("/api/v1/control-panel/overview")
async def control_panel_overview(request: Request) -> Response:
    return await proxy_to_legacy(request)
