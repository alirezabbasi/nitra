from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
LEGACY_PATH = ROOT / "legacy" / "app.py"


def load_legacy_module(path: Path = LEGACY_PATH):
    spec = importlib.util.spec_from_file_location("nitra_legacy_charting_app", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load legacy app from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


LEGACY_MODULE = load_legacy_module()
LEGACY_APP = LEGACY_MODULE.app
