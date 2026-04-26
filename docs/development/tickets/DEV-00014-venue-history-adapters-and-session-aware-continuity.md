# DEV-00014: Venue History Adapters and Session-Aware 90-Day Continuity

## Status

Done (live runtime evidence captured on 2026-04-26)

## Summary

Complete the missing runtime pieces for manual/automatic 90-day backfill:

- implement Capital historical adapter,
- route around Coinbase Exchange 403 path with alternate public candles route,
- enforce a deterministic continuity policy for closed-market minutes (FX weekends).

## Scope

- Add `capital` historical candles fetch in charting backfill path (`POST /api/v1/backfill/90d`).
- Add Coinbase fallback route when Exchange candles endpoint is blocked (403/429/5xx).
- Apply continuity policy:
  - `oanda`/`capital` non-crypto symbols: required continuity excludes weekend-closed minutes.
  - crypto symbols: required continuity is all minutes (`24/7`).
- Preserve explicit status output fields (`complete_90d_1m`, missing counts, adapter error reason).

## Non-Goals

- Replacing existing ingestion connectors.
- Rewriting deterministic Rust replay path in this ticket.
- Implementing exchange-calendar holidays beyond the weekend policy baseline.

## Implementation Notes

- Capital adapter:
  - session bootstrap: `POST /api/v1/session` with `X-CAP-API-KEY`
  - historical prices: `GET /api/v1/prices/{epic}?resolution=MINUTE&from=...&to=...&max=...`
  - token refresh on 401/403; optional `CAPITAL_EPIC_MAP` for canonical symbol -> epic mapping.
- Coinbase adapter:
  - primary: Exchange endpoint `api.exchange.coinbase.com/products/{product}/candles`
  - fallback: Advanced Trade public endpoint `api.coinbase.com/api/v3/brokerage/market/products/{product}/candles`
- Continuity policy:
  - session-aware missing-minute generation (SQL expected-series filtered for weekend closure where applicable).

## Acceptance Criteria

- Capital backfill attempts historical fetch via authenticated adapter.
- Coinbase backfill attempts fallback route when Exchange endpoint is blocked.
- Coverage completeness reflects required session minutes (not raw wall-clock minutes for closed FX windows).
- Endpoint response includes deterministic policy and error details for operational diagnostics.

## Deliverables

- Runtime code updates in `services/charting/app.py`
- Adapter health probe endpoint `POST /api/v1/backfill/adapter-check` for live-network diagnostics
- Explicit range backfill endpoint `POST /api/v1/backfill/window` (`from_ts`/`to_ts`)
- Coverage observability endpoints:
  - `GET /api/v1/coverage/status`
  - `GET /api/v1/coverage/metrics`
- Compose/env contract updates for charting adapter credentials and fallback endpoints
- LLD + env docs updates
- Test pack baseline under `tests/dev-0014`

## Runtime Evidence

- Evidence report: `docs/development/debugging/reports/live-runtime-evidence-dev-00013-00014-2026-04-26.md`
- Live adapter-check probes executed for `coinbase/BTCUSD`, `oanda/EURUSD`, and `capital/EURUSD`.
- Endpoint diagnostics returned explicit operational errors under current network constraints (`Network is unreachable`, `timed out`, `Temporary failure in name resolution`), confirming adapter observability and surfaced error behavior.
