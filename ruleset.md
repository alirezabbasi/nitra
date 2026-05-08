# NITRA + Eshel Root Ruleset

This file is the root-level project ruleset for NITRA.
It adopts Eshel as the mandatory AI-native engineering operating system for this repository.

## Rule 0: Scope and Precedence

- `ruleset.md` is the top-level ruleset for root governance.
- `docs/ruleset.md` is the execution baseline for full-project implementation behavior.
- `docs/design/ingestion/ruleset.md` is mandatory for ingestion-domain scope.
- If a conflict appears, apply the stricter rule unless an ADR explicitly approves an exception.

## Rule 1: Eshel Operating Model Is Mandatory

- NITRA development must follow the Eshel compounding loop:
  `idea -> structured knowledge -> task -> implementation -> verification -> bug management -> RCA -> updated knowledge`.
- Durable reasoning must not remain only in chat; it must be persisted in repository artifacts.

## Rule 2: Required Session Start Context

At each session start, run `make session-bootstrap` and load:

1. `ruleset.md`
2. `docs/ruleset.md`
3. `schema/*.md`
4. `wiki/index.md`
5. `wiki/project-brief.md`
6. recent `wiki/log.md`
7. `docs/development/04-memory/WHERE_ARE_WE.md`
8. `docs/development/04-memory/CURRENT_STATE.md`
9. `docs/development/02-execution/KANBAN.md`

## Rule 3: Task and Quality Gate Discipline

- Task artifacts must satisfy `schema/TASKS.md`.
- `make wiki-health` is required before closing meaningful implementation scopes.
- Missing critical wiki/governance artifacts are release-blocking quality failures.

## Rule 4: Traceability and Evidence

- Bugs must be recorded in `docs/development/debugging/BUG-*.md`.
- Debug commands must be logged in `docs/development/debugging/debugcmd.md`.
- Session outcomes must be reflected in durable memory artifacts and appended to `wiki/log.md`.
