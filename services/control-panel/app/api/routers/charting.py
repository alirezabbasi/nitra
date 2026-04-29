from fastapi import APIRouter, Request, Response

from app.services.charting.legacy_proxy import proxy_charting, proxy_charting_alias

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


# Compatibility bridge: keep pre-extraction paths live with deprecation headers.
@router.get("/api/v1/markets/available")
async def legacy_markets_available(request: Request) -> Response:
    return await proxy_charting_alias(request, replacement="/api/v1/charting/markets/available")


@router.get("/api/v1/bars/hot")
async def legacy_bars_hot(request: Request) -> Response:
    return await proxy_charting_alias(request, replacement="/api/v1/charting/bars/hot")


@router.get("/api/v1/bars/history")
async def legacy_bars_history(request: Request) -> Response:
    return await proxy_charting_alias(request, replacement="/api/v1/charting/bars/history")


@router.get("/api/v1/ticks/hot")
async def legacy_ticks_hot(request: Request) -> Response:
    return await proxy_charting_alias(request, replacement="/api/v1/charting/ticks/hot")


@router.get("/api/v1/venues")
async def legacy_venues(request: Request) -> Response:
    return await proxy_charting_alias(request, replacement="/api/v1/charting/venues")


@router.post("/api/v1/venues")
async def legacy_venues_upsert(request: Request) -> Response:
    return await proxy_charting_alias(request, replacement="/api/v1/charting/venues")


@router.get("/api/v1/venues/{venue}/markets")
async def legacy_venue_markets(request: Request) -> Response:
    return await proxy_charting_alias(request, replacement="/api/v1/charting/venues/{venue}/markets")


@router.post("/api/v1/venues/{venue}/markets")
async def legacy_venue_markets_upsert(request: Request) -> Response:
    return await proxy_charting_alias(request, replacement="/api/v1/charting/venues/{venue}/markets")


@router.post("/api/v1/backfill/adapter-check")
async def legacy_backfill_adapter_check(request: Request) -> Response:
    return await proxy_charting_alias(request, replacement="/api/v1/charting/backfill/adapter-check")


@router.post("/api/v1/backfill/90d")
async def legacy_backfill_90d(request: Request) -> Response:
    return await proxy_charting_alias(request, replacement="/api/v1/charting/backfill/90d")


@router.post("/api/v1/backfill/window")
async def legacy_backfill_window(request: Request) -> Response:
    return await proxy_charting_alias(request, replacement="/api/v1/charting/backfill/window")


@router.get("/api/v1/coverage/status")
async def legacy_coverage_status(request: Request) -> Response:
    return await proxy_charting_alias(request, replacement="/api/v1/charting/coverage/status")


@router.get("/api/v1/coverage/metrics")
async def legacy_coverage_metrics(request: Request) -> Response:
    return await proxy_charting_alias(request, replacement="/api/v1/charting/coverage/metrics")
