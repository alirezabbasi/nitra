#!/usr/bin/env bash
set -euo pipefail

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

# 1) Compliant repo shape must pass.
scripts/policy/check_technology_enforcement.sh >/dev/null
scripts/policy/check_contract_policy.sh >/dev/null

# 2) New python deterministic-core addition must fail.
python - <<'PY' "$TMP_DIR"
import json
import pathlib
import sys

tmp = pathlib.Path(sys.argv[1])
policy = json.loads(pathlib.Path("policy/technology-allocation.yaml").read_text())
new_service = {
    "id": "new_det_core_python",
    "catalog_ref": "## 1. Market Ingestion Service",
    "layer": "deterministic_core",
    "allowed_runtimes": ["rust"],
    "current_runtime": "python",
    "owner_status": "compliant",
    "repo_paths": [],
    "contracts": {
        "openapi_ref": "docs/design/nitra_system_lld/03_openapi_contracts.md",
        "asyncapi_ref": "docs/design/nitra_system_lld/04_asyncapi_event_contracts.md"
    }
}
policy["services"].append(new_service)
(tmp / "policy_python_core_fail.yaml").write_text(json.dumps(policy, indent=2))
PY
if POLICY_FILE="$TMP_DIR/policy_python_core_fail.yaml" scripts/policy/check_technology_enforcement.sh >/dev/null 2>&1; then
  echo "[dev-0010] expected python deterministic-core violation but check passed"
  exit 1
fi

# 3) Manifest/service-catalog mismatch must fail.
python - <<'PY' "$TMP_DIR"
import json
import pathlib
import sys

tmp = pathlib.Path(sys.argv[1])
policy = json.loads(pathlib.Path("policy/technology-allocation.yaml").read_text())
policy["services"][0]["catalog_ref"] = "## 999. Missing Service Heading"
(tmp / "policy_catalog_mismatch.yaml").write_text(json.dumps(policy, indent=2))
PY
if POLICY_FILE="$TMP_DIR/policy_catalog_mismatch.yaml" scripts/policy/check_technology_enforcement.sh >/dev/null 2>&1; then
  echo "[dev-0010] expected catalog mismatch violation but check passed"
  exit 1
fi

# 4) Unauthorized dual implementation must fail.
python - <<'PY' "$TMP_DIR"
import json
import pathlib
import sys

tmp = pathlib.Path(sys.argv[1])
policy = json.loads(pathlib.Path("policy/technology-allocation.yaml").read_text())
target = policy["services"][0]
target["migration"] = {
    "rust_target": "services/market-ingestion (rewrite in place)",
    "migration_ticket": "DEV-TEST-DUAL",
    "waiver_id": "",
    "dual_paths": ["services/market-ingestion", "services/market-normalization"],
}
(tmp / "policy_dual_impl_no_waiver.yaml").write_text(json.dumps(policy, indent=2))
PY
if POLICY_FILE="$TMP_DIR/policy_dual_impl_no_waiver.yaml" scripts/policy/check_technology_enforcement.sh >/dev/null 2>&1; then
  echo "[dev-0010] expected dual implementation no-waiver violation but check passed"
  exit 1
fi

echo "[dev-0010] checks passed"
