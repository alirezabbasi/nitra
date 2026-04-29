#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

fail() {
  echo "[dev-0045] FAIL: $1" >&2
  exit 1
}

echo "[dev-0045] checking architecture freeze artifacts..."
ticket="docs/development/tickets/DEV-00045-control-panel-target-architecture-and-migration-contract-freeze.md"
lld="docs/design/ingestion/07-devdocs/04-lld-services/control-panel-service.md"
map="docs/design/ingestion/07-devdocs/04-lld-services/control-panel-service-migration-map.md"

[[ -f "$ticket" ]] || fail "missing DEV-00045 ticket"
[[ -f "$lld" ]] || fail "missing control-panel-service LLD"
[[ -f "$map" ]] || fail "missing migration map artifact"

rg -n 'Backend Module Ownership|Frontend Module Ownership|Compatibility Header Contract|Rollout Sequence and Rollback Contract' "$lld" >/dev/null || fail "LLD missing frozen architecture sections"
rg -n 'Backend Migration Map|Frontend Migration Map|API Compatibility Matrix|Rollout and Fallback Contract' "$map" >/dev/null || fail "migration map missing required sections"
rg -n 'DEV-00046|DEV-00047|DEV-00048|DEV-00049|DEV-00050|DEV-00051' "$map" >/dev/null || fail "migration map missing downstream ticket links"

echo "[dev-0045] PASS"
