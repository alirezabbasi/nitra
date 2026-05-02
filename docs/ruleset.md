# NITRA Global Master Ruleset

This file is the umbrella ruleset for the full `nitra` project.
All contributors and AI agents must read and follow this file before planning or coding.

## Rule 0: Scope and Precedence

- `docs/ruleset.md` is the global baseline for the whole repository.
- Subdomain rulesets (for example `docs/design/ingestion/ruleset.md`) are mandatory inside their own scope.
- When a global and a subdomain rule conflict, apply the stricter rule unless an ADR explicitly approves an exception.

## Rule 1: Documentation Is Mandatory and Structured

- Documentation must remain current for architecture, delivery, operations, and testing.
- Primary documentation roots are:
  - `docs/design/` for project-wide architecture and planning.
  - `docs/design/ingestion/` for ingestion-domain details.
- Every meaningful implementation change must include matching documentation updates in the same change set.

## Rule 2: Authoritative Architecture Baseline

- `docs/design/nitra_system_hld.md` is the execution-facing HLD for implementation tracking.
- `docs/design/AI-enabled_trading_decision_platform.md` is the strategic architecture baseline and principle source.
- `docs/design/ARCHITECTURE_DECISIONS.md` ADR-0001 is the mandatory runtime technology allocation policy.
- All epics/stories must include an HLD alignment check before implementation and before closure.
- Any divergence requires ADR + migration/update notes and synchronized HLD updates.

## Rule 3: Domain Rulebooks Must Be Respected

- Contributors must load and follow domain-specific rulebooks when working in that domain.
- Ingestion domain source of truth: `docs/design/ingestion/ruleset.md`.
- Additional domain rulebooks may be added later and must be treated the same way.

## Rule 4: Docker-First Runtime Is Mandatory

- Development and server runtime must be operable via Docker Compose from repository root.
- Root folder is the deployable unit.
- Services must not require undocumented host-level manual runtime steps beyond Docker/Compose prerequisites.
- Every runnable service must keep Dockerfile + Compose contract in sync.

## Rule 5: CI/CD Readiness Is a Permanent Requirement

- Every service must support containerized build/test/release workflows.
- Branch, release, tagging, and promotion conventions must stay automation-friendly.
- Security and quality checks are required gates for deployable changes.

## Rule 6: Respect Existing Contracts

- Do not break architecture, API, schema, or data contracts without explicit ADR and migration notes.
- Section 5.1 technology allocation policy must pass hard gates via `make enforce-section-5-1`.

## Rule 7: Small, Traceable, Step-Based Delivery

- Keep changes small and reviewable with clear intent.
- Every implemented change must be committed; completed work must not be left uncommitted.
- When a task is finished in any chat/session, commit the related changes in that same session with a clear, scope-accurate commit message.
- Commit messages are mandatory explanations of the change: what was changed, why it was changed, and the scope boundary.
- This commit-with-explanation rule is permanent across restarts/resumes; session handoff does not relax commit requirements.
- Separate commits by scope (runtime, tests, docs, infra/config) with auditable messages.
- SDLC commit order per step should be: implementation -> tests -> docs (or a tightly scoped equivalent).

## Rule 8: Test-First SDLC by Project Step

- Every implemented scope must include tests aligned to that step.
- Tests should be organized under root `tests/` by epic/story when applicable.
- Relevant tests must be run before commit, before merge, and before release/promotion.
- A feature is not done without updated tests, test execution evidence, and test-scope documentation updates.
- Every non-completed ticket must contain an explicit `Definition of Done` section; new tickets are invalid without it.

## Rule 9: Safety, Operability, and Data Permanence First

- Prefer reliability, observability, backup/restore readiness, and rollback safety over speed-only shortcuts.
- Project/runtime data is permanent by default in dev and prod.
- Destructive deletion patterns are prohibited by default, including:
  - `docker compose down -v`
  - `docker volume rm`
  - `docker system prune`
  - file deletion commands targeting project/runtime data
- Any destructive action requires explicit owner approval and documented backup/rollback evidence.

## Rule 10: Environment and Configuration Discipline

- Keep `dev`, `paper/staging`, and `prod` aligned via explicit configuration.
- All env vars must have documented schema, defaults, and validation behavior.
- Secrets must never be committed in code or plain-text env files.

## Rule 11: Session Resume Context Reload Is Mandatory

- At the start of each session (or after pause/handoff/context switch), reload:
  - documentation entrypoint (`docs/README.md`),
  - repository instructions (`AGENTS.md` when present),
  - this global ruleset (`docs/ruleset.md`),
  - authoritative HLDs (`docs/design/nitra_system_hld.md`, `docs/design/AI-enabled_trading_decision_platform.md`),
  - authoritative LLD folder (`docs/design/nitra_system_lld`),
  - development state (`docs/development/04-memory/CURRENT_STATE.md`, `docs/development/02-execution/KANBAN.md`),
  - relevant domain docs/rulesets for the active scope.

## Rule 12: Mandatory Bug Registry

- Every discovered bug must be recorded under `docs/development/debugging/` with a unique code (`BUG-00001` style).
- Bug records must include:
  - description and impact,
  - reproducible steps,
  - root cause,
  - fix details,
  - verification evidence and status.
- Bug documentation should be updated in the same change set as the fix whenever feasible.

## Rule 13: Network Access Proxy Fallback

- For internet/image-pull failures (timeout/connection), retry via `proxychains`.
- Prefer direct access first; proxy fallback is recovery path.
- Document proxy-related reproducibility assumptions in applicable DevOps docs.

## Rule 14: "Where Are We?" Status Response Is Mandatory

- When asked "Where are we?" provide a concise structured status with exactly these sections:
  - Completed
  - Recent
  - Current
  - Next
  - Risks/Blocks
- The response must be sourced from:
  - `docs/development/04-memory/CURRENT_STATE.md`
  - `docs/development/04-memory/SESSION_LEDGER.md`
  - `docs/development/02-execution/KANBAN.md`
- After each substantial session, update these sources so future status answers remain accurate.

## Rule 15: Debug Command Logging Is Mandatory

- The main debugging documents folder is `docs/development/debugging`.
- Development and debugging commands must be logged in `docs/development/debugging/debugcmd.md` with timestamp, command text, and purpose.
- Add log entries continuously during active debugging/development sessions (do not defer to session end only).
- If a command fails, record failure status and short reason/evidence in the same entry.

## Rule 16: Control Panel Is Mandatory Project Control Surface

- The control panel is a first-class product surface and operational control plane for the whole project.
- New platform capabilities are not considered complete unless they are integrated into the control panel under the relevant module/section.
- Required per-feature control-panel integration includes:
  - operator visibility (health/status/telemetry),
  - configuration management controls where applicable,
  - role-based access control and audit trail coverage for privileged actions,
  - links to runbook/evidence workflows for operationally sensitive actions.
- Any feature lacking control-panel integration must remain `incomplete` in execution tracking until the companion UI/management scope is delivered.
- Control-panel UX/design direction must be maintained as an explicit architecture/value artifact under `docs/design/`.
