# DEV-00053: Control Panel Ingestion KPI Monitor

## Goal

Add a dedicated control-panel page to track two operational KPIs for all active instruments:

1. `1m` OHLCV coverage progress toward target (`~130k` rows per market).
2. Realtime raw tick health (`raw_tick` recency / lag SLA).

## Scope

- Backend endpoint: `/api/v1/control-panel/ingestion/kpi`
- Frontend workspace: `KPI Monitor`
- Proxy route in `services/control-panel`
- Role visibility update to expose `kpi` section.

## Contracts

- Query params:
  - `target_1m_bars` (default `130000`)
  - `tick_sla_seconds` (default `120`)
  - `row_limit`
- Response:
  - aggregate KPI metrics
  - per-market rows with coverage progress, last bar time, tick recency, and pass/warn status.

## Definition of Done

A ticket is complete only when all conditions below are true:

- Acceptance Criteria are fully met without unresolved scope gaps.
- Required implementation is merged in this repository and aligned with HLD/LLD constraints.
- Tests are added/updated for the scope and passing evidence is recorded.
- Operational/documentation artifacts for the scope are updated (runbooks/contracts/docs as applicable).
- Execution tracking and memory artifacts are synchronized (`KANBAN`, `CURRENT_STATE`, `SESSION_LEDGER`).
- Residual risks, assumptions, and follow-up actions are explicitly documented.

## Verification

- `make test-dev-0053`
- `make test-dev-0050`
- `make enforce-section-5-1`
