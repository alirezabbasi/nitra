#!/usr/bin/env bash
set -euo pipefail

echo "[dev-0064] verifying DEV-00064 roadmap conversion artifacts..."

TICKET="docs/development/tickets/DEV-00064-next-roadmap-slice-feature-platform-contract-and-shadow-readiness.md"
KANBAN="docs/development/02-execution/KANBAN.md"
FOCUS="docs/development/02-execution/ACTIVE_FOCUS.md"

[[ -f "$TICKET" ]] || { echo "missing ticket file: $TICKET"; exit 1; }

grep -q "## Acceptance Criteria" "$TICKET" || { echo "ticket missing Acceptance Criteria"; exit 1; }
grep -q "make test-dev-0064" "$TICKET" || { echo "ticket missing verification command"; exit 1; }
grep -q "DEV-00064" "$KANBAN" || { echo "kanban missing DEV-00064 reference"; exit 1; }
grep -q "DEV-00064" "$FOCUS" || { echo "active focus missing DEV-00064 reference"; exit 1; }

echo "[dev-0064] PASS"
