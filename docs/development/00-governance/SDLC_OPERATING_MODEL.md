# NITRA SDLC Operating Model

## Purpose

Provide a repeatable execution model for business-led direction and AI-assisted engineering delivery.

## Collaboration model

- Business/Product owner (you):
  - define priorities, acceptance intent, and business constraints.
  - validate solution direction and tradeoffs.
- Engineering executor (Codex):
  - translate goals into technical slices.
  - implement, test, and document with full traceability.
  - maintain project memory artifacts so work resumes cleanly.

## Work unit standard

Each work unit (ticket/story) must include:

- ID (`DEV-XXXXX` currently)
- scope and non-goals
- HLD alignment note
- acceptance criteria
- definition of done (DoD) section with completion gates
- verification evidence
- residual risks

## Required delivery sequence

1. HLD/LLD alignment check
2. implementation
3. tests
4. docs
5. commit with explanatory message (what changed, why, scope)
6. memory update (`CURRENT_STATE`, `SESSION_LEDGER`, decision/risk logs)

## Definition of done

A scope is done only when all are true:

- behavior implemented
- tests added/updated and run evidence captured
- relevant docs updated
- board status updated
- memory artifacts updated

Ticket-level enforcement:

- Every ticket in backlog or in-progress state must include a `## Definition of Done` section.
- New tickets are not valid for execution tracking until DoD is present.

## Session discipline

At start of each session:

1. reload required architecture/ruleset docs
2. read `04-memory/CURRENT_STATE.md`
3. read `02-execution/KANBAN.md`
4. confirm active objective

At end of each session:

1. append `04-memory/SESSION_LEDGER.md`
2. update `04-memory/CURRENT_STATE.md`
3. update `04-memory/WHERE_ARE_WE.md`
4. update board and any affected ticket status
5. commit all completed scope in that same session with a scope-accurate explanatory message

Commit persistence requirement:

- Restarting/resuming a session never waives commit requirements.
- Any completed implementation without an explanatory commit is considered non-compliant.

## Mandatory status command behavior

When asked "Where are we?", always respond using:

1. Completed
2. Recent
3. Current
4. Next
5. Risks/Blocks

Source priority:

1. `docs/development/04-memory/WHERE_ARE_WE.md`
2. `docs/development/04-memory/CURRENT_STATE.md`
3. `docs/development/04-memory/SESSION_LEDGER.md`
4. `docs/development/02-execution/KANBAN.md`

## Escalation policy

Pause and escalate to owner before implementing when:

- architecture contract changes are required
- cross-module tradeoff is non-obvious
- production safety/risk controls are impacted

## Enforcement Workflow (Section 5.1)

All PR-ready changes must pass:

1. `make enforce-section-5-1`

This command runs hard policy gates:

- technology allocation enforcement
- contract policy enforcement

Exception process:

- temporary exceptions require ADR-linked waiver entries with explicit expiry
- no waiver means no merge for non-compliant scope

Pre-commit sequence (standard):

1. `make policy-check`
2. relevant `tests/dev-*` packs for changed scope
