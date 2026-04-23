# EPIC-25: Decision-to-Execution Lineage Model

## Scope
- Implement full deterministic lineage across decision and execution entities.
- Close HLD Section 6 gaps for `order_intent`, `broker_order`, and `trade_decision`.

## Deliverables
- Durable linkage model from signal/risk decision to order intent and broker order state.
- Cross-entity correlation IDs and query views for lifecycle audits.
- Deterministic reconciliation rules for decision/execution drift.

## Acceptance
- Any fill can be traced backward to originating trade decision and policy checks.

## Commit Slices
1. `feat(lineage): add order_intent broker_order trade_decision model`
2. `feat(oms): persist end-to-end decision execution links`
3. `test(lineage): add backward traceability and drift checks`
