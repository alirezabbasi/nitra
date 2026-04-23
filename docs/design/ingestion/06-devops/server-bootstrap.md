# Server Bootstrap Plan

## Baseline Host Requirements

- Linux server with current Docker Engine.
- Docker Compose v2 plugin.
- Minimum CPU/RAM/disk sized to workload profile.
- NTP time sync enabled.
- Firewall policy with minimal open ports.

## Bootstrap Procedure

1. Copy project root folder to server.
2. Create `.env` from `.env.example` with server-specific values.
3. Create directories/volumes for persistence and backups.
4. Run `docker compose up -d`.
5. Verify health via `docker compose ps` and readiness endpoints.

## Post-Bootstrap Validation

- Redpanda reachable and topics manageable.
- TimescaleDB writable and migration-ready.
- ClickHouse reachable for analytics.
- MinIO reachable and bucket policy configured.
- Grafana stack healthy and dashboards loading.

## Non-Functional Requirements

- Startup must be deterministic.
- Restart must preserve data volumes.
- Recovery after host reboot must be automatic for core services.
