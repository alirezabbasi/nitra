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
3. Runs source session by adapter mode:
   - `oanda`: consumes line-delimited pricing stream.
   - `capital`: authenticates and polls latest minute prices per configured epic.
   - `coinbase`: opens websocket, subscribes to channels, extracts ticker/trade events.
4. Emits periodic health snapshots.
5. On session failure, emits degraded health and reconnects after configured backoff.

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
