#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT_DIR:-$(pwd)}"
POLICY_FILE="${POLICY_FILE:-$ROOT/policy/technology-allocation.yaml}"
WAIVER_FILE="${WAIVER_FILE:-$ROOT/policy/waivers.yaml}"
SERVICE_CATALOG_FILE="${SERVICE_CATALOG_FILE:-$ROOT/docs/design/nitra_system_lld/01_service_catalog.md}"
SERVICES_ROOT="${SERVICES_ROOT:-$ROOT/services}"

python - "$POLICY_FILE" "$WAIVER_FILE" "$SERVICE_CATALOG_FILE" "$SERVICES_ROOT" <<'PY'
import datetime as dt
import json
import sys
from pathlib import Path

policy_file = Path(sys.argv[1])
waiver_file = Path(sys.argv[2])
catalog_file = Path(sys.argv[3])
services_root = Path(sys.argv[4])

errors: list[str] = []

def fail(code: str, msg: str) -> None:
    errors.append(f"POLICY_ERROR:{code}:{msg}")

for file_path, code in ((policy_file, "missing_policy"), (waiver_file, "missing_waiver"), (catalog_file, "missing_catalog")):
    if not file_path.exists():
        fail(code, f"required file not found: {file_path}")

if errors:
    print("\n".join(errors))
    sys.exit(1)

policy = json.loads(policy_file.read_text(encoding="utf-8"))
waiver_data = json.loads(waiver_file.read_text(encoding="utf-8"))
catalog_text = catalog_file.read_text(encoding="utf-8")

allowed_layers = {"deterministic_core", "probabilistic_ai", "ui"}
allowed_status = {"compliant", "non_compliant_migrating", "blocked"}
waivers = {w["id"]: w for w in waiver_data.get("waivers", [])}
today = dt.date.today()

covered_paths = set()

for svc in policy.get("services", []):
    sid = svc.get("id", "<unknown>")
    layer = svc.get("layer")
    status = svc.get("owner_status")
    allowed_runtimes = set(svc.get("allowed_runtimes", []))
    current_runtime = svc.get("current_runtime")
    catalog_ref = svc.get("catalog_ref")

    if layer not in allowed_layers:
        fail("invalid_layer", f"{sid} has invalid layer '{layer}'")
    if status not in allowed_status:
        fail("invalid_status", f"{sid} has invalid owner_status '{status}'")

    if not catalog_ref or catalog_ref not in catalog_text:
        fail("catalog_diverge", f"{sid} missing catalog_ref match: {catalog_ref}")

    for rel in svc.get("repo_paths", []):
        covered_paths.add(rel)

    if layer == "deterministic_core":
        if "rust" not in allowed_runtimes or "python" in allowed_runtimes:
            fail("deterministic_runtime_policy", f"{sid} deterministic core must allow only rust")
    elif layer == "probabilistic_ai":
        if "python" not in allowed_runtimes or "rust" in allowed_runtimes:
            fail("ai_runtime_policy", f"{sid} probabilistic/ai must allow only python")
    elif layer == "ui":
        if "typescript" not in allowed_runtimes:
            fail("ui_runtime_policy", f"{sid} ui must allow typescript")

    if current_runtime == "none" and status == "blocked":
        pass
    elif current_runtime not in allowed_runtimes:
        if status != "non_compliant_migrating" and not (layer == "ui" and status == "blocked"):
            fail("runtime_noncompliant", f"{sid} current_runtime={current_runtime} violates allowed runtimes without migration status")

    if layer == "deterministic_core" and current_runtime == "python":
        if status != "non_compliant_migrating":
            fail("python_core_introduced", f"{sid} deterministic core running in python is not marked non_compliant_migrating")
        mig = svc.get("migration", {})
        if not mig.get("migration_ticket"):
            fail("missing_migration_ticket", f"{sid} missing migration ticket")
        waiver_id = mig.get("waiver_id")
        if not waiver_id:
            fail("missing_waiver", f"{sid} missing waiver_id")
        else:
            waiver = waivers.get(waiver_id)
            if not waiver:
                fail("invalid_waiver", f"{sid} references unknown waiver '{waiver_id}'")
            else:
                try:
                    expiry = dt.date.fromisoformat(waiver["expires_on"])
                except Exception:
                    fail("invalid_waiver_expiry", f"{sid} waiver '{waiver_id}' has invalid expires_on")
                else:
                    if expiry < today:
                        fail("expired_waiver", f"{sid} waiver '{waiver_id}' expired on {expiry.isoformat()}")
                if waiver.get("adr_id") != "ADR-0001":
                    fail("waiver_adr_mismatch", f"{sid} waiver '{waiver_id}' must reference ADR-0001")

    mig = svc.get("migration", {})
    dual_paths = mig.get("dual_paths", [])
    if dual_paths:
        both_exist = all((Path.cwd() / p).exists() for p in dual_paths)
        waiver_id = mig.get("waiver_id")
        if both_exist and not waiver_id:
            fail("dual_impl_no_waiver", f"{sid} has dual implementation paths without waiver")
        if both_exist and waiver_id and waiver_id not in waivers:
            fail("dual_impl_invalid_waiver", f"{sid} dual implementation waiver '{waiver_id}' not found")

# Detect untracked runnable service directories.
if services_root.exists():
    for child in services_root.iterdir():
        if not child.is_dir():
            continue
        rel = f"services/{child.name}"
        if child.name == "ingestion":
            continue
        if rel in covered_paths:
            continue
        # Consider it a runnable service if Dockerfile/app entry exists.
        if (child / "Dockerfile").exists() or (child / "app.py").exists():
            fail("untracked_service", f"service directory '{rel}' not declared in policy manifest")

if errors:
    print("\n".join(errors))
    sys.exit(1)

print("POLICY_OK:technology_enforcement")
PY
