from pathlib import Path
import importlib.util
import os

ROOT = Path(__file__).resolve().parents[2]
LEGACY_PATH = ROOT / "legacy" / "app.py"
LEGACY_CHARTING_PATH = ROOT / "charting" / "app.py"


def resolve_legacy_path() -> Path:
    candidate = os.getenv("LEGACY_CHARTING_APP_PATH")
    if candidate:
        env_path = Path(candidate)
        if env_path.exists():
            return env_path
    if LEGACY_CHARTING_PATH.exists():
        return LEGACY_CHARTING_PATH
    return LEGACY_PATH


def load_legacy_module(path: Path | None = None):
    module_path = path or resolve_legacy_path()
    if not module_path.exists():
        raise RuntimeError(f"legacy app path not found: {module_path}")
    spec = importlib.util.spec_from_file_location("nitra_legacy_charting_app", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load legacy app from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


LEGACY_MODULE = load_legacy_module()
LEGACY_APP = LEGACY_MODULE.app
