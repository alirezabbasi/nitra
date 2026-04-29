from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "control-panel"}


@router.get("/api/v1/config")
def config() -> dict:
    return {
        "service": "control-panel",
        "compat_mode": "native-charting-cutover",
        "legacy_charting_aliases": "retired",
    }


@router.get("/api/v1/control-panel/migration/status")
def migration_status() -> dict:
    return {
        "phase": "cutover-closed",
        "legacy_shims": "retired",
        "rollback_command": "scripts/ci/control_panel_refactor_quality_gate.sh",
    }
