# Canonical Normalization (EPIC-04)

## Objective

Convert raw broker events into canonical quote events with stable symbol identity and schema.

## Input Contract

- Topic: `raw.market.oanda` (configurable)
- Message format: `Envelope<RawMarketEvent>`

## Output Contract

- Topic: `normalized.quote.fx` (configurable)
- Message format: `Envelope<CanonicalEvent>`

## Normalization Rules

1. Resolve `(venue, broker_symbol)` through symbol registry.
2. Parse quote prices from broker payload (`bids/asks` or closeout fallback).
3. Validate price relationship (`ask >= bid`, both positive).
4. Derive canonical mid price.
5. Parse exchange timestamp from payload time field with fallback.
6. Emit `CanonicalEvent` with `event_type=Quote`.

## Failure Behavior

- Missing mapping: drop by default (or passthrough if explicitly enabled).
- Invalid quote payload: drop and log warning.
- Publish failure: treated as runtime error and triggers reconnect loop.
