# 04 — AsyncAPI / Event Contracts (LLD Draft)

## Event Backbone Rules
- Kafka topic names are dot-separated, domain-first.
- Schemas versioned explicitly with suffix `.v1`, `.v2`, etc.
- Events are immutable.
- Corrections are emitted as new events, not in-place rewrites.
- Partition keys chosen for ordering-critical domains.

---

## 1. Topic Catalog

### Market Data
- `md.raw.ticks.v1`
- `md.raw.trades.v1`
- `md.raw.orderbook.v1`
- `md.norm.ticks.v1`
- `md.norm.trades.v1`
- `md.norm.orderbook.v1`
- `md.bars.1s.v1`
- `md.bars.1m.v1`
- `md.bars.5m.v1`
- `md.bars.15m.v1`

### Structure
- `structure.snapshot.v1`
- `structure.pullback.v1`
- `structure.minor_confirmed.v1`
- `structure.major_confirmed.v1`

### Features / ML
- `features.snapshot.v1`
- `decision.signal_scored.v1`
- `ml.model_registered.v1`

### Risk / Portfolio / Execution
- `portfolio.snapshot.v1`
- `decision.risk_checked.v1`
- `exec.intent_created.v1`
- `exec.order_submitted.v1`
- `exec.order_updated.v1`
- `exec.fill_received.v1`
- `exec.reconciliation_issue.v1`

### Ops
- `ops.feed_health.v1`
- `ops.data_quality.v1`
- `ops.policy_violation.v1`
- `ops.alert_triggered.v1`

---

## 2. Event Envelope

```json
{
  "event_id": "uuid",
  "event_type": "structure.snapshot.v1",
  "event_version": 1,
  "occurred_at": "2026-04-21T12:00:00Z",
  "produced_at": "2026-04-21T12:00:00Z",
  "trace_id": "uuid",
  "source_service": "structure-engine",
  "partition_key": "BINANCE:BTCUSDT:5m",
  "payload": {}
}
```

---

## 3. Example Payloads

### `structure.snapshot.v1`
```json
{
  "symbol": "BTCUSDT",
  "venue": "BINANCE",
  "timeframe": "5m",
  "snapshot_id": "uuid",
  "directional_bias": "bearish",
  "liquidity_objective": {
    "side": "lower",
    "target_price": 1800.0
  },
  "active_reference": {
    "candle_id": "bar-12345",
    "high": 2101.0,
    "low": 2079.5
  },
  "pullback_state": "extended",
  "minor_archive_size": 17,
  "major_active": true,
  "created_at": "2026-04-21T12:00:00Z"
}
```

### `decision.risk_checked.v1`
```json
{
  "decision_id": "uuid",
  "signal_event_id": "uuid",
  "strategy_id": "ms-liquidity-v1",
  "approved": true,
  "rejection_reasons": [],
  "max_allowed_qty": 2.5,
  "risk_snapshot_id": "uuid",
  "checked_at": "2026-04-21T12:00:00Z"
}
```

### `exec.order_updated.v1`
```json
{
  "order_id": "uuid",
  "broker_order_id": "abc-123",
  "symbol": "BTCUSDT",
  "status": "partially_filled",
  "filled_qty": 1.0,
  "remaining_qty": 1.5,
  "avg_fill_price": 2050.25,
  "updated_at": "2026-04-21T12:00:01Z"
}
```

---

## 4. Partitioning Rules

### Ordered by symbol/timeframe
Topics:
- `md.bars.*`
- `structure.*`
- `features.snapshot.v1`

Partition key:
- `venue:symbol:timeframe`

### Ordered by order id
Topics:
- `exec.order_updated.v1`
- `exec.fill_received.v1`

Partition key:
- `order_id`

### Ordered by strategy/account
Topics:
- `decision.risk_checked.v1`
- `portfolio.snapshot.v1`

Partition key:
- `account_id:strategy_id`

---

## 5. Compatibility Rules
- backward-compatible additions only within same major version
- breaking changes require topic version bump
- schema registry enforcement mandatory
- dead-letter topics required for validation failures
