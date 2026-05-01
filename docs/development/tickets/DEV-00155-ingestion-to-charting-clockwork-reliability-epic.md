# DEV-00155: Ingestion->Charting Clockwork Reliability Epic

## Status

Planned

## Goal

Make the full market-data loop operationally reliable and deterministic under sustained live and replay load:

`ingestion -> normalization -> bars -> gaps -> backfill -> replay -> charting`

Reliability target: dependable "clockwork" behavior with measurable SLO/SLA gates, deterministic recovery, and explicit fail states.

## Scope

- Define end-to-end reliability contract for the full loop.
- Implement reliability gates and observability for each stage transition.
- Close current known risk gaps in feed quality, normalization integrity, queue recovery, and replay convergence.
- Establish readiness pass/fail criteria that must hold continuously, not only in one-off snapshots.
- Add control-panel/operator visibility for reliability status and degradation causes.

## Non-Goals

- Adding new venues or strategy features unrelated to loop reliability.
- Expanding ML/research scope before deterministic data-loop reliability is proven.

## Reliability Contract (Epic-Level)

- Stage continuity:
  - No silent drop between any adjacent stages in the loop.
  - Every stage must emit auditable counters and lag metrics.
- Recovery determinism:
  - Backfill/replay must converge to bounded queues and bounded lag under normal upstream availability.
  - Duplicate/out-of-order handling must be deterministic and idempotent.
- Coverage integrity:
  - Startup and rolling windows converge to required `1m` coverage policy per venue/session rules.
- Operator trust:
  - Charting reflects deterministic backend state; visible mismatches are explicitly surfaced as degraded/error status.

## Acceptance Criteria

- Epic child tickets for each reliability gap are linked and tracked to closure.
- End-to-end reliability dashboard/report exists with objective pass/fail thresholds per stage.
- A deterministic "clockwork" validation run passes for at least one sustained burn-in window.
- Known unresolved blockers (network/source unavailable, unknown markets, lag storms) are surfaced with explicit degraded states and runbook actions.
- Governance artifacts (`KANBAN`, `CURRENT_STATE`, `SESSION_LEDGER`) reflect reliable-loop readiness honestly.

## Child Ticket Map

- Existing foundational/reliability tickets (must be completed):
  - `DEV-00070`, `DEV-00075`, `DEV-00077`, `DEV-00078`, `DEV-00079`
  - `DEV-00142`, `DEV-00143`, `DEV-00144`, `DEV-00145`
- New execution ticket opened with this epic:
  - `DEV-00156` (clockwork reliability gate + burn-in validation harness)

## Definition of Done

A ticket is complete only when all conditions below are true:

- Acceptance Criteria are fully met without unresolved scope gaps.
- Required implementation is merged and aligned with HLD/LLD and rulesets.
- Tests are added/updated for the scope and passing evidence is recorded.
- Documentation and operational artifacts are updated as applicable.
- Execution tracking and memory artifacts are synchronized (`KANBAN`, `CURRENT_STATE`, `SESSION_LEDGER`).
- Residual risks and follow-up items are documented.

## Verification

- `make enforce-section-5-1`
- `make session-bootstrap`
- Epic burn-in gate command from `DEV-00156` must pass.

## Delivered Artifacts

- Reliability contract and gate definitions (to be delivered by child tickets).
- Evidence report for sustained burn-in reliability run.
