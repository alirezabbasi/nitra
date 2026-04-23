#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT_DIR:-$(pwd)}"
POLICY_FILE="${POLICY_FILE:-$ROOT/policy/technology-allocation.yaml}"

python - "$POLICY_FILE" <<'PY'
import json
import sys
from pathlib import Path

policy_file = Path(sys.argv[1])
errors = []

def fail(code: str, msg: str) -> None:
    errors.append(f"POLICY_ERROR:{code}:{msg}")

if not policy_file.exists():
    fail("missing_policy", f"required file not found: {policy_file}")
else:
    policy = json.loads(policy_file.read_text(encoding="utf-8"))
    for svc in policy.get("services", []):
        sid = svc.get("id", "<unknown>")
        status = svc.get("owner_status")
        layer = svc.get("layer")
        contracts = svc.get("contracts", {})

        if status == "blocked":
            continue

        for key in ("openapi_ref", "asyncapi_ref"):
            ref = contracts.get(key)
            if not ref:
                fail("missing_contract_decl", f"{sid} missing required contract field '{key}'")
                continue
            if not Path(ref).exists():
                fail("missing_contract_file", f"{sid} contract file not found: {ref}")

        if layer == "probabilistic_ai":
            ai_ref = contracts.get("ai_schema_ref")
            if not ai_ref:
                fail("missing_ai_schema_decl", f"{sid} missing ai_schema_ref")
            elif not Path(ai_ref).exists():
                fail("missing_ai_schema_file", f"{sid} ai schema file not found: {ai_ref}")

if errors:
    print("\n".join(errors))
    sys.exit(1)

print("POLICY_OK:contract_policy")
PY
