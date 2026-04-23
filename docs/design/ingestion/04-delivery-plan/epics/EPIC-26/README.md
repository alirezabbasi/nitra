# EPIC-26: Trade Outcome and Journal Completeness

## Scope
- Add explicit post-trade result entities and journal semantics.
- Close HLD Section 6 gap for `trade_outcome`.

## Deliverables
- Schema and lifecycle for trade outcomes (open/close attribution, pnl, slippage).
- Outcome computation jobs tied to fills and position closures.
- Operational journal views for post-trade reviews.

## Acceptance
- Every closed trade has a deterministic, auditable outcome record.

## Commit Slices
1. `feat(journal): add trade_outcome schema and lifecycle`
2. `feat(journal): compute pnl and slippage attribution`
3. `test(journal): add closed-trade outcome integrity tests`
