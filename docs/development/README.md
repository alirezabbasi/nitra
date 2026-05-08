# NITRA Development Operating System

This folder is the project-wide development control plane for NITRA.
It is designed to keep multi-session progress stable, traceable, and aligned with the HLD.

## Why this structure exists

NITRA development happens across multiple sessions and spans many modules beyond ingestion.
This layout prevents context loss and keeps execution aligned with business goals and SDLC quality gates.

## Folder Map

- `00-governance/`: delivery rules, ownership model, and session discipline.
- `01-roadmap/`: full-project module roadmap and sequencing aligned to HLD Section 5.
- `02-execution/`: active kanban and immediate execution focus.
- `03-delivery/`: delivered scope, module-by-module records, and implementation evidence.
- `04-memory/`: persistent project memory system (state snapshots, decisions, risks, handoff ledger).
- `debugging/`: canonical bug registry and debugging command log.
- `tickets/`: project ticket files retained for continuity and migration tracking.

## Mandatory read order at each resume

Run this command first at every session start:

- `make session-bootstrap`
- `make wiki-health` (before closing meaningful scope)

1. `docs/README.md`
2. `ruleset.md`
3. `docs/ruleset.md`
4. `schema/*.md`
5. `wiki/index.md`
6. `wiki/project-brief.md`
7. `wiki/log.md`
8. `docs/design/nitra_system_hld.md`
9. `docs/design/AI-enabled_trading_decision_platform.md`
10. `docs/development/04-memory/WHERE_ARE_WE.md`
11. `docs/development/04-memory/CURRENT_STATE.md`
12. `docs/development/02-execution/KANBAN.md`

## Existing records preserved

- Legacy kanban entrypoint: `docs/development/TODO.md` (now points to canonical board).
- Existing tickets remain under `docs/development/tickets/` for stable references.
- Ingestion runbook and reuse map are canonicalized under `03-delivery/ingestion/artifacts/`; compatibility pointers are kept at legacy paths.

## Governance alignment

This workspace is governed by:

- Root ruleset (Eshel OS baseline): `ruleset.md`
- Global ruleset: `docs/ruleset.md`
- Domain ruleset (ingestion scope): `docs/design/ingestion/ruleset.md`
- Agent workflow schemas: `schema/*.md`
- Persistent knowledge layer: `wiki/`

All meaningful implementation changes must update the related docs here in the same change set.
All completed implementation changes must also be committed in-session with an explanatory, scope-accurate commit message (what/why/scope), including after restart/resume.

## Ticket policy

- Every new ticket must include:
  - `## Acceptance Criteria`
  - `## Definition of Done`
- Backlog or in-progress tickets missing DoD are considered invalid until updated.
- `make session-bootstrap` enforces DoD presence for all non-completed tickets.
