#!/usr/bin/env bash
set -euo pipefail

echo "[dev-0065] verifying deterministic-first governance artifacts..."

MAP_DOC="docs/development/01-roadmap/DETERMINISTIC_EXECUTION_DEPENDENCY_MAP.md"
CRITERIA_DOC="docs/development/00-governance/SECTION5_CLOSURE_CRITERIA.md"
TICKET_DOC="docs/development/tickets/DEV-00065-program-governance-deterministic-first-execution-map-dependency-graph-and-closur.md"
KANBAN_DOC="docs/development/02-execution/KANBAN.md"

[[ -f "$MAP_DOC" ]] || { echo "missing dependency map doc"; exit 1; }
[[ -f "$CRITERIA_DOC" ]] || { echo "missing closure criteria doc"; exit 1; }

grep -q "P0 -> P1 -> P2 -> P3 -> P4 -> P5 -> P6 -> P7 -> P8" "$MAP_DOC" || { echo "missing priority chain"; exit 1; }
grep -q "Priority 0" "$KANBAN_DOC" || { echo "kanban missing priority sections"; exit 1; }
grep -q "Program-Level Exit Gates" "$CRITERIA_DOC" || { echo "missing program-level exit gates"; exit 1; }
grep -q "In Progress\\|Done" "$TICKET_DOC" || { echo "ticket status missing"; exit 1; }
grep -q "DETERMINISTIC_EXECUTION_DEPENDENCY_MAP.md" "$TICKET_DOC" || { echo "ticket not linked to map artifact"; exit 1; }
grep -q "SECTION5_CLOSURE_CRITERIA.md" "$TICKET_DOC" || { echo "ticket not linked to criteria artifact"; exit 1; }

echo "[dev-0065] PASS"
