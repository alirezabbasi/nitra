# EPIC-21: Market Event Canonical Persistence

## Scope
- Persist canonical market micro-events as first-class entities.
- Close HLD Section 6 gaps for `raw_tick`, `book_event`, and `trade_print`.

## Deliverables
- Timescale schema for `raw_tick`, `book_event`, `trade_print` with idempotency keys.
- Connector/normalizer persistence path updates for multi-venue ingestion.
- Replay-safe ingestion and deduplication tests.

## Acceptance
- OANDA/CAPITAL/COINBASE event persistence is replay-safe with zero silent loss.

## Commit Slices
1. `feat(data): add raw_tick book_event trade_print persistence schema`
2. `feat(ingest): persist multi-venue canonical micro-events`
3. `test(data): add replay and dedupe validation for micro-events`
