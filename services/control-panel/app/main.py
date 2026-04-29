from pathlib import Path
import importlib.util

from fastapi import FastAPI

from app.api.routers.health import router as health_router


ROOT = Path(__file__).resolve().parents[1]
LEGACY_PATH = ROOT / "legacy" / "app.py"


def load_legacy_app(path: Path):
    spec = importlib.util.spec_from_file_location("nitra_legacy_charting_app", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load legacy app from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app


app = FastAPI(title="nitra-control-panel")
app.include_router(health_router)
app.mount("", load_legacy_app(LEGACY_PATH))
