	# 01 — Service Catalog

## 1. Market Ingestion Service
**Purpose**
- Connect to exchanges, brokers, and market data providers.
- Normalize transport-level payloads into raw internal event envelopes.

**Responsibilities**
- WebSocket/REST feed handling
- heartbeat supervision
- sequence integrity checks
- source timestamping
- publish raw events to Kafka
- persist raw copies to object storage

**Consumes**
- Exchange feeds
- Broker market-data feeds

**Produces**
- `md.raw.ticks.v1`
- `md.raw.trades.v1`
- `md.raw.orderbook.v1`
- `ops.feed_health.v1`

**Tech**
- Rust
- Tokio
- Kafka producer
- object storage client

**Scaling**
- partition by venue + symbol group

---

## 2. Market Normalization Service
**Purpose**
- Convert raw events into canonical market data structures.

**Responsibilities**
- symbol mapping
- timestamp normalization
- deduplication
- schema validation
- gap detection
- out-of-order handling
- canonical event emission

**Consumes**
- `md.raw.*`

**Produces**
- `md.norm.ticks.v1`
- `md.norm.trades.v1`
- `md.norm.orderbook.v1`
- `ops.data_quality.v1`

**Tech**
- Rust
- Kafka consumer groups
- schema validator

---

## 3. Bar Aggregation Service
**Purpose**
- Build OHLCV and derived bars from normalized market events.

**Responsibilities**
- bucket ticks into bars
- handle session rollover
- publish multi-timeframe bars
- emit bar-finalization events

**Consumes**
- `md.norm.ticks.v1`
- optional `md.norm.trades.v1`

**Produces**
- `md.bars.1s.v1`
- `md.bars.1m.v1`
- `md.bars.5m.v1`
- `md.bars.15m.v1`

**Storage**
- TimescaleDB

---

## 4. Structure Engine
**Purpose**
- Implement liquidity-driven market structure deterministically.

**Responsibilities**
- directional liquidity objective
- reference candle tracking
- pullback start/extension/termination
- inside/outside bar handling
- minor structure archive
- major structure activation
- fractal footprint markers
- structure-state snapshots

**Consumes**
- `md.bars.*`
- optional tick stream for intrabar termination validation

**Produces**
- `structure.snapshot.v1`
- `structure.pullback.v1`
- `structure.minor_confirmed.v1`
- `structure.major_confirmed.v1`

**Tech**
- Rust
- explicit state machine
- snapshot persistence

**Hard Rule**
- This service is the single source of truth for structure state.

---

## 5. Feature Service
**Purpose**
- Materialize online and offline features.

**Responsibilities**
- feature view definitions
- point-in-time joins
- online serving
- offline dataset generation
- feature versioning
- feature freshness supervision

**Consumes**
- market data
- structure snapshots
- portfolio state
- external data (optional)

**Produces**
- online feature responses
- feature materialization batches
- `features.snapshot.v1`

**Tech**
- Feast
- PostgreSQL/Redis depending on latency tier

---

## 6. Research Orchestrator
**Purpose**
- Manage dataset creation, labeling, backtests, and experiments.

**Responsibilities**
- replay job orchestration
- strategy evaluation
- walk-forward validation
- labeling pipeline
- train/test split governance
- experiment tracking

**Tech**
- Python
- MLflow
- orchestration jobs on Kubernetes

**Boundary**
- No direct write path into live execution services.

---

## 7. Model Training Service
**Purpose**
- Train and register signal/regime/anomaly models.

**Responsibilities**
- data pulls from feature store
- train/evaluate models
- log metrics/artifacts
- register models
- attach signatures and metadata
- publish promotion candidates

**Produces**
- MLflow model versions
- `ml.model_registered.v1`

---

## 8. Online Inference Gateway
**Purpose**
- Serve signal models and aggregate inference results.

**Responsibilities**
- score entry/exit candidates
- regime classification
- anomaly detection
- confidence calibration
- response schema enforcement

**Tech**
- Ray Serve

**Consumes**
- structure snapshots
- online features
- model registry metadata

**Produces**
- `decision.signal_scored.v1`

---

## 9. Risk Engine
**Purpose**
- Enforce all hard risk and compliance policies.

**Responsibilities**
- pre-trade checks
- position limits
- max loss / drawdown
- notional caps
- venue availability checks
- duplicate-order prevention
- kill-switch enforcement

**Consumes**
- signal events
- portfolio state
- account balances
- venue status

**Produces**
- `decision.risk_checked.v1`
- `ops.policy_violation.v1`

**Hard Rule**
- If this service is unavailable, trading fails closed.

---

## 10. Portfolio Engine
**Purpose**
- Maintain live portfolio and strategy state.

**Responsibilities**
- positions
- realized/unrealized PnL
- exposures
- cash and margin tracking
- strategy allocation state

**Produces**
- `portfolio.snapshot.v1`

---

## 11. Execution Gateway
**Purpose**
- Convert approved intents into broker/exchange orders.

**Responsibilities**
- order creation
- amend/cancel
- lifecycle tracking
- partial fill handling
- reconciliation
- timeout / retry logic
- slippage metrics

**Consumes**
- approved trade intents
- broker/exchange ack/fill streams

**Produces**
- `exec.order_submitted.v1`
- `exec.order_updated.v1`
- `exec.fill_received.v1`
- `exec.reconciliation_issue.v1`

**Hard Rule**
- This is the only service allowed to place or modify orders.

---

## 12. RAG Indexer
**Purpose**
- Index framework docs, examples, journals, and postmortems.

**Responsibilities**
- chunking
- embedding
- metadata tagging
- retention policies
- similarity-search indexing

**Storage**
- pgvector initially

---

## 13. LLM Analyst Service
**Purpose**
- Interpret structured state and retrieved context.

**Responsibilities**
- build prompts from state + retrieved context
- output schema-bound analysis
- produce critique and explanation
- flag ambiguity
- generate post-trade review drafts

**Hard Limits**
- cannot create orders
- cannot override risk
- cannot invent structure state

---

## 14. Audit and Observability Service
**Purpose**
- Persist audit trails and expose telemetry.

**Responsibilities**
- decision lineage
- trace correlation
- metrics export
- alert routing
- policy incident capture
- immutable event journaling
