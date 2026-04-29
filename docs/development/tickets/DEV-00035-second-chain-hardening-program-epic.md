# DEV-00035: Second-Chain Hardening Program Epic (Structure -> Journal)

## Status

Open

## Summary

Establish a strict delivery program to strengthen the deterministic chain:
`structure -> feature -> signal -> risk -> execution -> portfolio -> journal`.

## Scope

- Define and sequence all hardening tickets for second-chain reliability.
- Enforce contract-first execution with deterministic replay guarantees.
- Require explicit evidence and acceptance gates per chain stage.

## Non-Goals

- New UI programs outside second-chain hardening.
- Non-deterministic shortcuts in core trading runtime.

## Decomposed Tickets

1. `DEV-00036` cross-chain contracts, schema gates, and replay determinism.
2. `DEV-00037` structure-engine production deterministic hardening.
3. `DEV-00038` feature service deterministic baseline and point-in-time integrity.
4. `DEV-00039` signal engine deterministic scorer and explainability baseline.
5. `DEV-00040` risk policy expansion and traceability hardening.
6. `DEV-00041` execution lifecycle controls and reconciliation SLA hardening.
7. `DEV-00042` portfolio authoritative reconciliation and state invariants.
8. `DEV-00043` journal/audit evidence fabric and incident bundle export.

## Acceptance Criteria

- Ticket set is complete, ordered, and implementation-ready.
- Each ticket defines deterministic guardrails and verification.
- Kanban and memory docs explicitly reference second-chain hardening priority.

## Verification

- Documentation-only epic setup; no runtime changes in this ticket.
