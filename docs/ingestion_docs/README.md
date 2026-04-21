# Bars Flow Plus Documentation

This folder is the full revamp blueprint of `../barflow` into `barsfp` with the target stack:

- Rust
- Redpanda
- TimescaleDB (hot)
- ClickHouse (cold analytics)
- S3/MinIO lakehouse archive
- Grafana stack (Prometheus, Loki, Tempo, Grafana)

## Structure

- `00-source-review/`
Source analysis of legacy Barflow docs and implementation.

- `01-architecture/`
Target architecture, service boundaries, and ADR-level decisions.

- `02-data-platform/`
Canonical event model, topic contracts, storage design, retention rules.
Includes stream backbone and broker connector contracts.
Includes canonical normalization and symbol registry contracts.
Includes deterministic 1m bar engine and Timescale hot-store contracts.
Includes gap coverage and precision backfill/replay contracts.
Includes lakehouse archival contracts and manifest/checkpoint semantics.
Includes ClickHouse cold analytics schema, loader pipeline, and query split.

- `03-reliability-risk-ops/`
SLOs, risk controls, observability, runbook pack plan.
Includes non-bypassable risk gateway and OMS lifecycle/reconciliation policy docs.
Includes Prometheus/Loki/Tempo/Grafana observability and SLO alert policy docs.
Includes paper rollout runbook, micro-live checklist, rollback protocol, and emergency procedures.

- `04-delivery-plan/`
Epic roadmap, milestone gates, migration strategy, and commit-by-commit execution.
Includes per-epic folders in `04-delivery-plan/epics/`.
Includes final closure audit, sign-off, and known-limits records.

- `05-git-workflow/`
Repo bootstrap, branching strategy, commit conventions.

- `06-devops/`
Docker-first deployment contract, server bootstrap model, CI/CD blueprint, security, and operations requirements.

- `07-devdocs/`
Canonical developer guides and low-level design (LLD) onboarding material.
Includes onboarding flow, local development workflow, LLD architecture/data-model specs, and SDLC delivery standards for new contributors.

- `../tests/`
Step-based SDLC test packs organized by project epic.

## Source Documents Given Highest Priority

- `../barflow/docs/Automated Financial market trading system.md`
- `../barflow/docs/Multi-broker market data load.md`

Both have been used as primary design inputs for this revamp.
