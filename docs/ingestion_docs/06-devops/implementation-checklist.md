# DevOps Implementation Checklist

## Immediate Requirements

- [x] Add root `docker-compose.yml` covering EPIC-02 stream baseline (`redpanda`, console, topic init); expand to full stack in later epics.
- [x] Add shared Rust multi-target Dockerfile (`infra/docker/rust-services.Dockerfile`) and wire all Rust services through compose `target` stages.
- [x] Add `.env.example` with validated variable schema (initial stream variables).
- [x] Add startup healthchecks for core stream components.
- [x] Add persistent named volumes and retention policy notes (Redpanda + Timescale + lakehouse + ClickHouse volumes added and actively used by pipeline).
- [x] Add initial infrastructure Make targets (`up`, `down`, `ps`, `logs`, `health`).

## CI Requirements

- [ ] CI workflow for Rust fmt/lint/test (already started).
- [ ] CI workflow for container build verification.
- [ ] CI security checks (dependency, secret, and image scans).
- [ ] CI docs-check policy for runtime/deploy changes.
- [x] Step-based local test packs created under `tests/epic-XX/` with runnable scripts.

## CD Readiness Requirements

- [ ] Image tagging and registry push workflow.
- [ ] Environment promotion workflow (`dev` -> `paper/staging` -> `prod`).
- [x] Smoke and readiness verification gates (closure gate script enforces quick/full checks).
- [ ] Rollback automation or scripted rollback target.

## Operations Requirements

- [ ] Backups and restore scripts for stateful components.
- [~] Runbooks for deploy failure, data lag, storage failure, and rollback (core paper/micro-live/emergency docs added; expand incident depth).
- [x] Alert rules and dashboards for core service SLOs.
- [ ] Incident postmortem template and audit trail process.
