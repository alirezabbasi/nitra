---
type: task
status: done
---

# TASK-0001 — NITRA Eshel foundation adoption

## Context
- [[../systems/ai-native-engineering-os]]
- [[../project-brief]]

## Objective
Install the Eshel baseline operating artifacts inside NITRA and wire mandatory quality gates.

## Scope
- Add root-level Eshel-aligned ruleset.
- Add schema contracts and wiki baseline.
- Add wiki quality-gate automation and Make targets.

## Out of Scope
- Full migration of all existing `docs/development/tickets/` into `wiki/tasks/`.
- Historical backfill of all past sessions into structured wiki entities.

## Implementation Steps
1. Create `ruleset.md` and `schema/` contracts.
2. Create `wiki/` baseline artifacts.
3. Add `tools/` scripts and Make commands.
4. Update session/bootstrap and docs references.

## Acceptance Criteria
- `make wiki-health` runs and produces a report.
- Session bootstrap read order includes root ruleset + schema + wiki artifacts.
- Development docs explicitly state Eshel as mandatory workflow.

## Definition of Done
- Baseline artifacts are committed and referenced from docs.
- No critical wiki lint issues remain.

## Verification Commands
```bash
make wiki-health
make session-bootstrap
```

## Documentation Updates
- Update root `README.md` and `docs/development/README.md` with Eshel workflow.
