# NITRA Ingestion Domain Ruleset

This file is the permanent domain ruleset for the ingestion part of `nitra`.
All contributors and AI agents working on ingestion scope must read and follow this file before making changes.

## Rule 1: Documentation Is Mandatory and Structured

- The documentation root for this domain is `docs/ingestion_docs/`.
- Every meaningful ingestion change must include documentation updates in the same change set when applicable.
- Documents must be placed under the correct subject folder (`01-architecture`, `02-data-platform`, `03-reliability-risk-ops`, `06-devops`, `07-devdocs`, `bugs`, etc.).

## Rule 2: Docker-First Runtime Is Mandatory

- Ingestion services must run through Docker Compose as part of the repository root deployment.
- Services must not require undocumented host-level manual runtime steps beyond Docker/Compose prerequisites.
- Dockerfiles and Compose definitions are required artifacts for all runnable ingestion services.

## Rule 3: Production-Ready DevOps Plan Must Be Maintained

- DevOps documentation under `docs/ingestion_docs/06-devops/` is mandatory and must be updated alongside implementation.
- CI/CD requirements, release strategy, deployment strategy, rollback strategy, and operations standards must remain documented.
- Runtime behavior changes that break deployment contracts are prohibited without docs and migration notes.

## Rule 4: CI/CD Readiness Is a Permanent Requirement

- Every ingestion service must support containerized build/test/release workflows.
- Branch, release, tagging, and promotion practices must remain automation-friendly.
- Quality and security checks are mandatory gates before deployable changes.

## Rule 5: Respect Existing Contracts

- Do not break ingestion architecture, API, schema, or data contracts without explicit ADR and migration notes.

## Rule 6: Small, Traceable Changes

- Prefer small, reviewable commits with clear scope and intent.

## Rule 7: Mandatory Step-Based Commits (Strict)

- Every implemented change must be committed; completed work must not be left uncommitted.
- Commit scope must stay tight and separated by subject (runtime, tests, docs, infra/config).
- Each commit must have an auditable message.
- Step sequence should follow SDLC order: implementation -> tests -> docs (or tightly scoped equivalent).

## Rule 8: Safety and Operability First

- Favor reliability, observability, backup/restore readiness, and rollback safety over speed-only shortcuts.

## Rule 9: Environment Parity and Config Discipline

- Keep `dev`, `paper/staging`, and `prod` aligned through explicit configuration.
- Env vars must have documented schema, defaults, and validation behavior.
- Do not commit secrets in code or plain-text env files.

## Rule 10: Network Access Fallback via Proxy

- For image pulls and internet-related failures (timeout/connection), retry with `proxychains`.
- Prefer direct access first; proxy fallback is an operational recovery path.
- Document proxy assumptions when they affect reproducibility.

## Rule 11: Test-First SDLC Discipline by Step

- Every implemented ingestion scope must include tests aligned with the built step.
- Tests should be organized under root `tests/` by step/epic where applicable.
- Relevant tests must be run before commit, before merge, and before release/promotion.
- No feature is done without test changes, execution evidence, and updated test-scope docs.

## Rule 12: Data Permanence and No-Deletion Operations

- Project and database data must be treated as permanent by default.
- Destructive cleanup commands are prohibited by default (`docker compose down -v`, `docker volume rm`, `docker system prune`, deletion of runtime/project data).
- Any destructive action requires explicit owner approval plus backup/rollback evidence.

## Rule 13: HLD Alignment for Ingestion Scope

- Ingestion implementation must align with the project-authoritative HLD: `docs/design/AI-enabled_trading_decision_platform.md`.
- Ingestion design/LLD docs under `docs/ingestion_docs/` must stay synchronized with implementation.
- Divergence requires ADR + migration/update notes.

## Rule 14: Developer Guides and LLD Must Be Maintained

- `docs/ingestion_docs/07-devdocs/` is the canonical ingestion developer-guide and LLD path.
- Workflow, boundaries, contracts, schema, SDLC, testing, and release changes must update these docs in the same change set.

## Rule 15: Session Resume Must Reload Context

- At each session start (or after pause/handoff/context switch), reload:
  - repository instructions (`AGENTS.md` when present),
  - global ruleset (`docs/ruleset.md`),
  - ingestion ruleset (`docs/ingestion_docs/ruleset.md`),
  - authoritative HLD (`docs/design/AI-enabled_trading_decision_platform.md`),
  - relevant ingestion developer docs.

## Rule 16: Mandatory Bug Registry and Resolution Notes

- Every ingestion bug must be recorded under `docs/ingestion_docs/bugs/` with unique code (for example `BUG-00001`).
- Records must include description/impact, reproduction steps, root cause, fix details, verification evidence, and status.
- Bug documentation should be updated in the same change set as the fix whenever feasible.
