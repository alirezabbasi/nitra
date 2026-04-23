# EPIC-13: Durable Stateful Stream Engines

## Scope
- Persist stream engine state needed for deterministic restart behavior.
- Add startup recovery logic for bar and gap engines.

## Deliverables
- Durable checkpoint/state schema and retention strategy.
- Restart-recovery implementation for stateful processors.
- Consistency tests for restart and resume scenarios.

## Acceptance
- Restart drills show deterministic output continuity with no state drift.

## Commit Slices
1. `feat(state): add durable checkpoints for stream engines`
2. `test(state): add restart continuity and drift detection tests`
