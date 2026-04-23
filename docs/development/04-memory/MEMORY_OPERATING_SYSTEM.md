# Memory Operating System (MOS)

## Objective

Prevent strategic and technical drift across multi-session development.
Ensure every "Where are we?" request has an immediate, accurate, structured answer.

## Design principles

- persistent: memory is file-based and versioned in git
- explicit: decisions and assumptions are documented, not implied
- resumable: each session can restart from `CURRENT_STATE.md` + latest ledger entry
- audit-friendly: every major change has traceable rationale and evidence links

## Required memory artifacts

1. `CURRENT_STATE.md`
   - single source of truth for where the project stands now
   - must include the standardized "Where are we?" sections
2. `DECISION_LOG.md`
   - decisions with context, alternatives, impact
3. `RISKS_AND_ASSUMPTIONS.md`
   - open risks, confidence level, mitigation
4. `SESSION_LEDGER.md`
   - what happened in each session and what is next
5. `WHERE_ARE_WE.md`
   - concise status snapshot intended for direct response reuse

## Session protocol

### Session start

1. read `docs/ruleset.md`
2. read HLD documents
3. read `CURRENT_STATE.md`
4. read latest entry in `SESSION_LEDGER.md`
5. confirm active objective in `02-execution/ACTIVE_FOCUS.md`

### During session

- append decisions immediately when tradeoffs are resolved
- update risk register when new uncertainty appears

### Session end

- update `CURRENT_STATE.md`
- update `WHERE_ARE_WE.md`
- append ledger entry (date, summary, evidence, next steps)
- update board state in `02-execution/KANBAN.md`

## "Where are we?" response standard

When asked "Where are we?", respond with:

1. Completed
2. Recent
3. Current
4. Next
5. Risks/Blocks

Primary source order:

1. `WHERE_ARE_WE.md`
2. `CURRENT_STATE.md`
3. `SESSION_LEDGER.md`
4. `../02-execution/KANBAN.md`

## Ownership matrix

- Business owner: priorities, scope intent, acceptance direction
- Codex executor: implementation, testing, docs, memory update completeness
- Shared: decision approvals for high-impact architecture changes

## Efficiency rules

- keep current state concise and structured
- avoid duplicating long details; link to source docs/tickets
- treat stale memory as a defect; refresh before coding
