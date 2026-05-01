from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routers.auth_session import router as auth_session_router
from app.api.routers.charting import router as charting_router
from app.api.routers.config import router as config_router
from app.api.routers.execution import router as execution_router
from app.api.routers.health import router as health_router
from app.api.routers.ingestion import router as ingestion_router
from app.api.routers.ops import router as ops_router
from app.api.routers.overview import router as overview_router
from app.api.routers.research import router as research_router
from app.api.routers.risk_portfolio import router as risk_portfolio_router
from app.api.routers.search import router as search_router
from app.core.legacy_bridge import LEGACY_APP, LEGACY_MODULE



app = FastAPI(title="nitra-control-panel")
FRONTEND_DIST_DIR = Path(__file__).resolve().parents[1] / "frontend" / "dist"
LEGACY_STATIC_DIR = Path(getattr(LEGACY_MODULE, "STATIC_DIR", FRONTEND_DIST_DIR))
app.mount(
    "/control-panel-assets",
    StaticFiles(directory=str(FRONTEND_DIST_DIR)),
    name="control-panel-assets",
)


@app.get("/")
def root_control_panel() -> FileResponse:
    return FileResponse(str(FRONTEND_DIST_DIR / "control-panel.html"))


@app.middleware("http")
async def root_charting_override(request: Request, call_next):
    if request.url.path == "/":
        return FileResponse(str(FRONTEND_DIST_DIR / "control-panel.html"))
    if request.url.path == "/charting":
        return FileResponse(str(LEGACY_STATIC_DIR / "index.html"))
    return await call_next(request)


@app.get("/control-panel")
def control_panel() -> FileResponse:
    return FileResponse(str(FRONTEND_DIST_DIR / "control-panel.html"))


@app.get("/charting")
def charting_view() -> FileResponse:
    return FileResponse(str(LEGACY_STATIC_DIR / "index.html"))


app.include_router(health_router)
app.include_router(auth_session_router)
app.include_router(overview_router)
app.include_router(ingestion_router)
app.include_router(risk_portfolio_router)
app.include_router(execution_router)
app.include_router(ops_router)
app.include_router(research_router)
app.include_router(config_router)
app.include_router(search_router)
app.include_router(charting_router)

# Keep legacy app mounted during migration for parity on non-extracted routes.
app.mount("", LEGACY_APP)
