# EPIC-03: Broker Ingestion Adapters

## Scope
- Rust adapter runtime for OANDA, CAPITAL, and COINBASE feeds.
- Health events and reconnect policy.

## Deliverables
- Connector service crate with broker adapter modes.
- Heartbeat/reconnect/rate-limit controls.
- Raw event publishing and observability metrics.

## Acceptance
- 5-day paper ingest stability with zero unexplained feed blackout on each enabled adapter.

## Commit Slices
1. `feat(connector): implement oanda adapter collector`
2. `feat(connector): add heartbeat/reconnect and health events`
3. `feat(connector): add capital and coinbase adapters`
