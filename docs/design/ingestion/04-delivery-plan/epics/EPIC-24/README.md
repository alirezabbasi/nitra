# EPIC-24: Portfolio and Risk State Model

## Scope
- Promote risk and portfolio state to first-class durable entities.
- Reduce runtime-only risk decisions by grounding checks on persisted state.

## Deliverables
- Schema for `risk_state` and `portfolio_position` with update policies.
- Aggregation/update workflows from fills, orders, and market movements.
- Safety checks for exposure, concentration, and drawdown calculations.

## Acceptance
- Risk gateway decisions are reproducible from persisted risk and portfolio state.

## Commit Slices
1. `feat(risk): add risk_state and portfolio_position persistence`
2. `feat(risk): wire gateway checks to durable state`
3. `test(risk): add reproducibility and exposure consistency tests`
