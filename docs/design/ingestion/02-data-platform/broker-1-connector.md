# Broker Adapters (EPIC-03)

## Scope Implemented

- Unified connector service supports three explicit broker adapter modes:
  - `oanda` (`oanda-adapter` compose service)
  - `capital` (`capital-adapter` compose service)
  - `coinbase` (`coinbase-adapter` compose service)
- Raw events are wrapped in the stream envelope and published per venue:
  - `raw.market.oanda`
  - `raw.market.capital`
  - `raw.market.coinbase`
- Health telemetry events are published to `connector.health`.
- Reconnect loop and heartbeat emission are included for all adapters.

## Runtime Behavior

1. Adapter service boots from environment-based config.
2. Establishes publish path to Redpanda brokers.
3. Runs source session by adapter mode (venue APIs only; no synthetic generation):
   - `oanda`: pulls account pricing snapshot from OANDA API for configured instruments.
   - `capital`: authenticates session and fetches latest minute prices per configured epic/symbol mapping.
   - `coinbase`: fetches venue ticker snapshots per configured product.
4. Emits periodic health snapshots.
5. On session failure, emits degraded health and retries; it never substitutes mock prices.

## Failover Policy Contract (DEV-00068)

- Per-venue failover policy is operator-managed via control-panel contract:
  - `GET /api/v1/control-panel/ingestion`
    - includes `failover_policies` and `failover_runtime`.
  - `POST /api/v1/control-panel/ingestion/failover-policy`
    - guarded update path with RBAC + justification + audit trail.
- Policy fields:
  - `enabled`
  - `primary_endpoint`
  - `secondary_endpoints`
  - `failure_threshold`
  - `cooldown_seconds`
  - `reconnect_backoff_seconds`
  - `max_backoff_seconds`
  - `request_timeout_seconds`
  - `jitter_pct`

## Key Environment Variables

Common:
- `CONNECTOR_MODE`
- `CONNECTOR_VENUE`
- `CONNECTOR_RAW_TOPIC`
- `CONNECTOR_HEALTH_TOPIC`
- `CONNECTOR_HEARTBEAT_SECS`
- `CONNECTOR_RECONNECT_BACKOFF_SECS`
- `REDPANDA_BROKERS`

OANDA adapter:
- `OANDA_STREAM_URL`
- `OANDA_API_TOKEN`

CAPITAL adapter:
- `CAPITAL_API_URL`
- `CAPITAL_API_KEY`
- `CAPITAL_IDENTIFIER`
- `CAPITAL_API_PASSWORD`
- `CAPITAL_EPIC_ALLOWLIST`
- `CAPITAL_POLL_INTERVAL_SECS`

COINBASE adapter:
- `COINBASE_WS_URL`
- `COINBASE_PRODUCT_ALLOWLIST`
- `COINBASE_CHANNELS`

## Current Contract

Published raw payload schema:
- envelope with `message_id`, `emitted_at`, `schema_version`, `headers`, `payload`
- payload includes `venue`, `broker_symbol`, `event_ts_received`, `source`, and original broker JSON payload

Health payload schema:
- `venue`, `mode`, `status`, `emitted_count`, `error_count`, `last_error`, `event_ts`
