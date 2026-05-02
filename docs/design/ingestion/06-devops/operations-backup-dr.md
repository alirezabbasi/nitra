# Operations, Backup, and Disaster Recovery

## SRE/Operations Baseline

- Service health and readiness probes required.
- Metrics/logs/traces exported to Grafana stack.
- Alerts must map to actionable runbooks.

## Backup Plan

- TimescaleDB scheduled backups and restore drill cadence.
- ClickHouse backup policy for analytical data durability.
- MinIO bucket replication/versioning strategy.
- Configuration backup for Compose and environment manifests.

## DR Plan

- Define RPO/RTO targets by environment.
- Warm restore plan for same-region recovery.
- Cold restore plan for catastrophic failure.
- Quarterly recovery drills with evidence logs.

## DEV-00073 Backup/DR Restore Drill Runbook

- Run restore drill evidence logging through control panel:
  - `POST /api/v1/control-panel/ingestion/raw-lake/restore-drill`
- Maintain per-environment retention/tiering policy through control panel:
  - `POST /api/v1/control-panel/ingestion/raw-lake/retention-policy`
- Required evidence fields for each drill:
  - environment, validation window, object/row counts, checksum match, restore duration, final status, operator notes.
- Minimum cadence:
  - `dev`: every 24h validation window.
  - `staging`: weekly validation.
  - `prod`: monthly validation with checksum evidence retention.

## Operational Readiness Criteria

- Rollback procedure tested.
- On-call runbooks validated.
- SLO dashboard coverage in place.
- Data integrity checks automated for hot/cold/archive flows.
