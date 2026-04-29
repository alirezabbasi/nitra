from fastapi import APIRouter, Request, Response

from app.services.charting.legacy_proxy import proxy_charting

router = APIRouter()


@router.get("/api/v1/control-panel/charting/profile")
async def control_panel_charting_profile(request: Request) -> Response:
    return await proxy_charting(request)


@router.get("/api/v1/charting/markets/available")
async def charting_markets_available(request: Request) -> Response:
    return await proxy_charting(request)


@router.get("/api/v1/charting/bars/hot")
async def charting_bars_hot(request: Request) -> Response:
    return await proxy_charting(request)


@router.get("/api/v1/charting/bars/history")
async def charting_bars_history(request: Request) -> Response:
    return await proxy_charting(request)


@router.get("/api/v1/charting/ticks/hot")
async def charting_ticks_hot(request: Request) -> Response:
    return await proxy_charting(request)


@router.get("/api/v1/charting/venues")
async def charting_venues(request: Request) -> Response:
    return await proxy_charting(request)


@router.post("/api/v1/charting/venues")
async def charting_venues_upsert(request: Request) -> Response:
    return await proxy_charting(request)


@router.get("/api/v1/charting/venues/{venue}/markets")
async def charting_venue_markets(request: Request) -> Response:
    return await proxy_charting(request)


@router.post("/api/v1/charting/venues/{venue}/markets")
async def charting_venue_markets_upsert(request: Request) -> Response:
    return await proxy_charting(request)


@router.post("/api/v1/charting/backfill/adapter-check")
async def charting_backfill_adapter_check(request: Request) -> Response:
    return await proxy_charting(request)


@router.post("/api/v1/charting/backfill/90d")
async def charting_backfill_90d(request: Request) -> Response:
    return await proxy_charting(request)


@router.post("/api/v1/charting/backfill/window")
async def charting_backfill_window(request: Request) -> Response:
    return await proxy_charting(request)


@router.get("/api/v1/charting/coverage/status")
async def charting_coverage_status(request: Request) -> Response:
    return await proxy_charting(request)


@router.get("/api/v1/charting/coverage/metrics")
async def charting_coverage_metrics(request: Request) -> Response:
    return await proxy_charting(request)
