# Coverage Debt Before/After Report

- Date: `2026-04-26`
- Timezone: `+0330` (Asia/Tehran)
- Window: rolling `90 days` at `1m`
- Cleanup script executed:
  - `docs/development/debugging/sql/2026-04-26-one-time-cleanup-legacy-unknown-market-backfill.sql`

## 1) Before Cleanup

### Unknown-market backlog (`backfill_jobs`)

| venue | canonical_symbol | status | jobs |
| --- | --- | --- | ---: |
| coinbase | EURUSD | queued | 11983 |
| coinbase | DOGEUSD | queued | 90 |
| coinbase | DOGEUSD | completed | 15 |

### Backlog status counts

| table | status | rows |
| --- | --- | ---: |
| backfill_jobs | completed | 29489 |
| backfill_jobs | partial | 4004 |
| backfill_jobs | queued | 129073 |
| replay_audit | completed | 29489 |
| replay_audit | failed | 55088 |
| replay_audit | partial | 4004 |
| replay_audit | queued | 158503 |

## 2) Cleanup Execution Result

| metric | value |
| --- | ---: |
| unknown_jobs_total | 12088 |
| backfill_rows_marked_failed_unknown_market | 12073 |
| replay_rows_marked_failed | 2623 |
| gap_rows_marked_ignored_unknown_market | 14 |

## 3) After Cleanup

### Unknown-market backlog (`backfill_jobs`)

| venue | canonical_symbol | status | jobs |
| --- | --- | --- | ---: |
| coinbase | EURUSD | failed_unknown_market | 11983 |
| coinbase | DOGEUSD | failed_unknown_market | 90 |
| coinbase | DOGEUSD | completed | 15 |

### Backlog status counts

| table | status | rows |
| --- | --- | ---: |
| backfill_jobs | completed | 29489 |
| backfill_jobs | failed_unknown_market | 12073 |
| backfill_jobs | partial | 4004 |
| backfill_jobs | queued | 117000 |
| replay_audit | completed | 29489 |
| replay_audit | failed | 57711 |
| replay_audit | partial | 4004 |
| replay_audit | queued | 155880 |

## 4) Backlog Delta (After - Before)

| metric | delta |
| --- | ---: |
| backfill_jobs.queued | -12073 |
| replay_audit.queued | -2623 |
| replay_audit.failed | +2623 |

Interpretation:
- Unknown-market queued backlog was drained into terminal statuses.
- Valid queued workload is now more visible and less polluted by invalid market pairs.

## 5) Coverage Debt (Before vs After)

Coverage debt was effectively unchanged by cleanup (expected for status-only cleanup):

- Worst debt remained on index/metals symbols (`oanda/capital` `NAS100`, `US30`, `XAUUSD`) with very low filled minutes.
- Strongest coverage remained on Coinbase majors (`BTCUSD`, `ETHUSD`, `ADAUSD`, `SOLUSD`, `XRPUSD`).

Sample comparison (before -> after):

| venue | symbol | debt_before | debt_after |
| --- | --- | ---: | ---: |
| capital | NAS100 | 129484 | 129484 |
| capital | US30 | 129484 | 129484 |
| oanda | NAS100 | 129484 | 129484 |
| oanda | US30 | 129484 | 129484 |
| coinbase | BTCUSD | 36 | 37 |

Note:
- Small ±1 minute differences can occur because the rolling 90-day window advances during measurement.

## 6) Conclusion

Cleanup/drain policy worked as intended:
- No data deletion.
- Legacy unknown-market backlog normalized to terminal statuses.
- Queue is cleaner for valid symbol convergence work.
