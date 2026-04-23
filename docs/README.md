# NITRA Documentation System

This is the canonical documentation entrypoint for the full NITRA project.

## Start Here

1. `docs/ruleset.md` (global rules and mandatory behavior)
2. `docs/design/README.md` (architecture authority and design map)
3. `docs/development/README.md` (execution system, kanban, and memory)
4. `docs/design/ingestion/README.md` (ingestion domain rulebook and deep technical docs)

## Documentation Layers

- `docs/design/`: architecture source of truth (HLD/LLD and design decisions).
- `docs/development/`: delivery operating system (roadmap, execution board, project memory).
- `docs/design/ingestion/`: ingestion-domain deep docs, contracts, runbooks, and domain bug registry.

## Single-source principles

- Architecture truth lives in `docs/design/`.
- Execution truth lives in `docs/development/02-execution/KANBAN.md` and `docs/development/04-memory/CURRENT_STATE.md`.
- Domain implementation details live in domain folders (currently `docs/design/ingestion/`).

## "Where are we?" quick answer protocol

When asked "Where are we?", answer using this structure:

1. Completed: latest closed slices/tickets.
2. Recent: what happened in the latest session(s).
3. Current: what is in progress right now.
4. Next: the next 1-3 concrete actions.
5. Risks/Blocks: any blockers or decision points.

Primary sources for this answer:

- `docs/development/04-memory/CURRENT_STATE.md`
- `docs/development/04-memory/SESSION_LEDGER.md`
- `docs/development/02-execution/KANBAN.md`
