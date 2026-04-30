# Section 5 Closure Criteria Contract

## Purpose

Define objective closure gates for deterministic-first Section 5 completion.

## Ticket-Level Close Criteria

A ticket may be moved to `Done` only when all are true:

1. Scope implementation merged and runnable in docker-first runtime.
2. Deterministic verification exists and passes (relevant `make test-*` target).
3. Section 5.1 policy gate passes (`make enforce-section-5-1`).
4. Session consistency gate passes (`make session-bootstrap`).
5. Documentation and runbook changes are updated in the same change set.
6. If applicable, control-panel companion scope is also complete (Rule 16 compliance).

## Priority-Level Exit Gates

### P0 Exit Gate

- All P0 component tickets complete.
- `DEV-00124..DEV-00126` complete.
- Feed reliability evidence includes failover/session/rate-limit/raw capture conformance.
- Raw lake + Kafka replayability checks pass.

### P1 Exit Gate

- All P1 component tickets complete.
- `DEV-00127..DEV-00129` complete.
- Normalization/replay determinism and structure replay conformance evidenced.

### P2 Exit Gate

- Research validation pack complete.
- `DEV-00131` complete.

### P3 Exit Gate

- Feature platform and inference scopes complete.
- `DEV-00130` and `DEV-00132` complete.

### P4 Exit Gate

- Risk/portfolio deterministic policy and fail-closed scenarios complete.
- `DEV-00133` complete.

### P5 Exit Gate

- Execution lifecycle/reconciliation deterministic conformance complete.
- `DEV-00134` complete.

### P6 Exit Gate

- OTel + metrics + alerting + lineage complete.
- `DEV-00136` complete.

### P7 Exit Gate

- MLflow promotion governance (`DEV-00095`) complete with deterministic evidence.

### P8 Exit Gate

- Advisory-only AI scopes complete with policy boundaries intact.
- `DEV-00135` complete.

## Program-Level Exit Gates

Program closure requires:

1. All P0->P8 tickets complete.
2. Cross-cutting platform/security/config tickets complete.
3. `DEV-00066` (traceability matrix) complete.
4. `DEV-00067` (readiness gate aggregator) complete.
5. `DEV-00140` (control-panel finalization) complete.
6. `DEV-00122` final evidence bundle accepted.

## Non-Negotiable Blockers

Section 5 completion is blocked if any of the below is true:

- Deterministic gates fail for core data/replay/risk/execution scopes.
- Control-panel companion ticket is incomplete for a completed component ticket.
- Policy gate or session integrity gate fails.
- Runtime requires undocumented manual host steps outside docker-first contract.
