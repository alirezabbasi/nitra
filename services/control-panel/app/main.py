from fastapi import FastAPI

from app.api.routers.auth_session import router as auth_session_router
from app.api.routers.config import router as config_router
from app.api.routers.execution import router as execution_router
from app.api.routers.health import router as health_router
from app.api.routers.ingestion import router as ingestion_router
from app.api.routers.ops import router as ops_router
from app.api.routers.overview import router as overview_router
from app.api.routers.research import router as research_router
from app.api.routers.risk_portfolio import router as risk_portfolio_router
from app.api.routers.search import router as search_router
from app.core.legacy_bridge import LEGACY_APP



app = FastAPI(title="nitra-control-panel")
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

# Keep legacy app mounted during migration for parity on non-extracted routes.
app.mount("", LEGACY_APP)
