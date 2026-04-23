# EPIC-06: Gap Coverage and Precision Backfill

## Scope
- Detect both tail and internal gaps.
- Backfill missing-only intervals with lock safety.

## Deliverables
- Coverage tables and gap detector service.
- Backfill worker and replay reconciliation.
- Gap lifecycle state machine.

## Acceptance
- No unnecessary refetch under restart/replay drills.

## Commit Slices
1. `feat(gaps): add coverage engine and internal gap detection`
2. `feat(backfill): add missing-only backfill and replay`
