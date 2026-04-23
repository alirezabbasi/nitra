# Deployment Contract

## Contract Goal

Any server with Docker Engine + Docker Compose plugin must be able to run BarsFP by:

1. Placing repository root on server.
2. Setting environment files.
3. Running `docker compose up -d` from repository root.

## Mandatory Deployable Artifacts

- `docker-compose.yml` at repository root.
- Rust service build definition (`infra/docker/rust-services.Dockerfile`) with compose targets for runnable services.
- `.env.example` with required variables.
- `Makefile` targets for bootstrap/health/teardown.
- Health/readiness endpoints for core services.
- `services/chart_ui/` static chart service assets and NGINX config for trader-facing visualization.

## Runtime Expectations

- No host-installed language runtimes required for normal run.
- No manual per-service start commands on host.
- All internal networking resolved via Compose network names.
- Data persistence through named volumes or documented bind mounts.
- Redpanda container runtime limits must include sufficient `nofile` capacity for configured topic partitions and DLQ topics.
- Chart UI must be externally reachable on `${CHART_UI_PORT:-8110}` and internally proxy `/api/*` to `query-api:8104`.

## Release Compatibility

- Compose definitions must remain backward-compatible across minor releases when possible.
- Breaking deployment changes require migration notes and rollback instructions.
