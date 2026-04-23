# Docker Compose Standards

## Compose Topology

Mandatory services for baseline stack:
- `redpanda`
- `timescaledb`
- `clickhouse`
- `minio`
- `prometheus`
- `loki`
- `tempo`
- `grafana`
- application services (`oanda-adapter`, `capital-adapter`, `coinbase-adapter`, `normalizer`, `bar_engine`, `gap_engine`, `backfill_worker`, `archive_worker`, `risk_gateway`, `oms`, `query_api`)
- application services (`oanda-adapter`, `capital-adapter`, `coinbase-adapter`, `normalizer`, `bar_engine`, `gap_engine`, `backfill_worker`, `archive_worker`, `risk_gateway`, `oms`, `query_api`, `chart-ui`)

## Standards

- Use explicit image tags, never floating `latest` in production paths.
- Use named volumes for persistent state.
- Use restart policy for long-running services.
- Use healthchecks for all critical components.
- Isolate internal services on private network.
- Expose only required external ports.
- If `chart-ui` is enabled, expose only `${CHART_UI_PORT:-8110}` externally and keep API/data stores on internal network names.
- Use Compose profiles where needed (`dev`, `ops`, `full`).
- Redpanda must run with elevated file-descriptor limits (`nofile`) sized for total partition count growth (primary + DLQ + internal topics).
- Topic-partition growth must be capacity-checked against Redpanda FD limits before new topic rollout.
- Rust services must build from a shared multi-target Dockerfile (`infra/docker/rust-services.Dockerfile`) to maximize local layer reuse.
- `rust-toolchain.toml` must stay pinned to an explicit version that matches builder base image.
- Rust base and dependency cache refresh must be intentional via Make targets:
  - `make rust-cache-warm`
  - `make rust-cache-refresh`

## Configuration Discipline

- Environment variables sourced from `.env` and service-level defaults.
- All required env vars documented in `.env.example` and DevOps docs.
- Secrets injected via secure method (runtime env/secret manager), not hardcoded.

## Operational Commands (Target State)

- `docker compose up -d`
- `docker compose ps`
- `docker compose logs -f <service>`
- `docker compose stop`

## Data Safety Constraint

- Destructive Docker cleanup commands are prohibited in normal workflows.
- Do not use commands that can remove persisted data/volumes.

## Network Failure Fallback

- If image pulls or internet-dependent operations fail with timeout/connectivity errors, retry using `proxychains`.
- Examples:
  - `proxychains docker compose pull`
  - `proxychains cargo fetch`
