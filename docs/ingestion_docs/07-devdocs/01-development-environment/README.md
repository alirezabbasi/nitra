# Development Environment Guide

## Canonical Workflow

1. Sync branch and inspect working tree.
2. Make small scoped changes.
3. Run targeted test pack (`tests/epic-xx/run.sh`).
4. Update docs (HLD/LLD/epic log where applicable).
5. Commit in subject-separated groups.

## Key Commands

- Full stack up: `docker compose up -d`
- Service status: `docker compose ps`
- Warm Rust Docker cache once for all Rust services: `make rust-cache-warm`
- Intentional Rust base/toolchain refresh + cache warm: `make rust-cache-refresh`
- Lint: `make lint`
- Tests: `make test`
- Epic tests: `make test-epic-03` (example)

## Rust Container Build Caching

- Rust services share a unified build definition at `infra/docker/rust-services.Dockerfile`.
- Compose services use Docker `target` stages from that file.
- This design compiles workspace binaries in a shared builder layer so repeated service builds reuse local Docker cache instead of re-downloading/recompiling.

## Environment Variables

- Baseline variables live in `.env.example`.
- Local overrides live in `.env`.
- New variables require:
  - `.env.example` update,
  - runtime validation in code,
  - docs update in `docs/07-devdocs/` and subject docs.

## Non-Destructive Rule

Never run destructive data cleanup commands by default.
Data and volumes are treated as permanent unless explicit owner-approved exception is documented.
