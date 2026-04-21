# Deterministic Bar Engine (EPIC-05)

## Objective

Build canonical 1-minute OHLC bars from normalized quote events with deterministic bucket behavior.

## Input Contract

- Topic: `normalized.quote.fx`
- Message type: `Envelope<CanonicalEvent>`
- Required fields: `venue`, `canonical_symbol`, `event_ts_exchange`, `mid`

## Output Contract

- Topic: `bar.1m`
- Message type: `Envelope<Bar>`

## Aggregation Rules

1. Bucket by UTC minute (`YYYY-MM-DD HH:MM:00`).
2. `open`: first mid in bucket.
3. `high`: max mid in bucket.
4. `low`: min mid in bucket.
5. `close`: last mid in bucket.
6. `trade_count`: number of contributing quote events.
7. Late events for already-advanced bucket are dropped to preserve deterministic progression.

## Finalization Rule

A bar is finalized when the next event for same `(venue, canonical_symbol)` enters a later minute bucket.
