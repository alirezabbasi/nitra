#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

fail() {
  echo "[dev-0044] FAIL: $1" >&2
  exit 1
}

echo "[dev-0044] checking control-panel refactor program baseline..."
ticket_epic="docs/development/tickets/DEV-00044-control-panel-service-refactor-program-epic.md"
[[ -f "$ticket_epic" ]] || fail "missing DEV-00044 epic ticket"
rg -n 'DEV-00045|DEV-00046|DEV-00047|DEV-00048|DEV-00049|DEV-00050|DEV-00051' "$ticket_epic" >/dev/null || fail "missing downstream ticket references in DEV-00044"

for child in \
  docs/development/tickets/DEV-00045-control-panel-target-architecture-and-migration-contract-freeze.md \
  docs/development/tickets/DEV-00046-control-panel-backend-modularization-foundation-and-service-rename.md \
  docs/development/tickets/DEV-00047-control-panel-domain-router-split-and-service-layer-extraction.md \
  docs/development/tickets/DEV-00048-control-panel-charting-module-extraction-and-compatibility-bridge.md \
  docs/development/tickets/DEV-00049-control-panel-frontend-app-shell-restructure-and-ui-architecture-hardening.md \
  docs/development/tickets/DEV-00050-control-panel-refactor-quality-gates-and-ci-readiness.md \
  docs/development/tickets/DEV-00051-control-panel-refactor-rollout-cutover-and-deprecation-closure.md; do
  [[ -f "$child" ]] || fail "missing child ticket: $child"
done

lld_doc="docs/design/ingestion/07-devdocs/04-lld-services/control-panel-service.md"
[[ -f "$lld_doc" ]] || fail "missing control-panel service LLD"
rg -n 'Backend Target Structure|Frontend Target Structure|Migration Contract' "$lld_doc" >/dev/null || fail "control-panel service LLD missing required sections"

echo "[dev-0044] PASS"
