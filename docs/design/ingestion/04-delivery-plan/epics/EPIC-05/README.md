# EPIC-05: Deterministic Bars and Timescale Hot Store

## Scope
- Build deterministic 1s/1m aggregation from canonical events.
- Implement Timescale schema and aggregate views.

## Deliverables
- Bar engine with close rules.
- Timescale hypertables + retention + aggregates.
- Hot query endpoints for recent market state.

## Acceptance
- Replay of identical input reproduces identical bars.

## Commit Slices
1. `feat(bars): implement deterministic 1s/1m bar builder`
2. `feat(timescale): add hot schema, indexes, retention jobs`
