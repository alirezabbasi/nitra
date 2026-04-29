from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "control-panel"}


@router.get("/api/v1/config")
def config() -> dict:
    return {
        "service": "control-panel",
        "compat_mode": "legacy-charting-bridge",
    }
