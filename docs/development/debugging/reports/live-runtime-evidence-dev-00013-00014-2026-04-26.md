# Live Runtime Evidence — DEV-00013 / DEV-00014

- Date: `2026-04-26`
- Timezone: `+0330` (Asia/Tehran)
- Compose scope: `backfill-worker`, `gap-detection`, `replay-controller`, `market-normalization`, `bar-aggregation`, `charting`, `timescaledb`, `kafka`

## 1) Compose Health Snapshot

`docker compose ps` confirmed all required ingestion/backfill services are up during capture.

## 2) Backfill / Replay Runtime SQL Evidence

Source: `timescaledb` via `docker compose exec -T timescaledb psql ...`

### `backfill_jobs` status counts

| status | rows |
| --- | ---: |
| completed | 29489 |
| failed_no_source_data | 90 |
| failed_unknown_market | 12073 |
| partial | 4005 |
| queued | 117000 |

### `replay_audit` status counts

| status | rows |
| --- | ---: |
| completed | 29489 |
| failed | 57801 |
| partial | 4005 |
| queued | 155880 |

### `gap_log` status counts

| status | rows |
| --- | ---: |
| backfill_queued | 286 |
| ignored_unknown_market | 14 |
| resolved | 145 |

## 3) Coverage / Adapter Runtime Evidence

Source: `charting` APIs on `localhost:8110`.

### Coverage metrics

- `nitra_coverage_symbols_total`: `17`
- `nitra_coverage_symbols_with_open_gaps`: `17`
- `nitra_coverage_ratio_avg`: `0.511807`
- `nitra_backfill_jobs_total{status="queued"}`: `68632`
- `nitra_replay_audit_total{status="queued"}`: `34374`

### Coverage status sample (`window_hours=2160`, `limit=5`)

- `symbols_total`: `5`
- `symbols_with_open_gaps`: `5`
- `coverage_ratio_avg`: `0.7790341123911081`
- Example rows include:
  - `coinbase/BTCUSD`: coverage ratio `0.9976852030462728`
  - `coinbase/ETHUSD`: coverage ratio `0.9922608621847053`
  - `coinbase/DOGEUSD`: coverage ratio `0.0035647873087399015`

### Adapter-check probes

- `coinbase/BTCUSD`: `status=error`, `Network is unreachable`
- `oanda/EURUSD`: `status=error`, `timed out`
- `capital/EURUSD`: `status=error`, `Temporary failure in name resolution`

These adapter-check results satisfy the DEV-00013 acceptance path of explicit surfaced error states when coverage cannot be completed due external network/source availability.

## 4) Closure Decision

- `DEV-00013`: runtime evidence captured with both completion and explicit surfaced error-state diagnostics.
- `DEV-00014`: adapter-check endpoints exercised in live runtime; diagnostics are explicit and operationally actionable.

Both tickets are ready to move from in-progress to done in execution/memory docs.
