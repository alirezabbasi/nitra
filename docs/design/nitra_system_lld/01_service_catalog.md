# 01 — Service Catalog

## 0. Global Enforcement Policy

This catalog is governed by ADR-0001 (`docs/design/ARCHITECTURE_DECISIONS.md`) and HLD Section 5.1.

Mandatory technology allocation:

- deterministic trading core: Rust-only
- probabilistic/ML/AI layer: Python-only
- operator/charting UI: TypeScript frontend

Mandatory control boundaries:

- LLM layer is advisory only
- only deterministic Rust execution path can place/modify/cancel orders
- if AI fails, deterministic path continues
- if risk/execution integrity is uncertain, trading fails closed

Anti-duplication rule:

- no parallel Python/Rust implementation of the same production core component

Migration state model:

- `compliant`
- `non_compliant_migrating` (requires ticket + waiver)
- `blocked` (no net-new feature scope while non-compliant)

Waiver process:

- temporary exceptions must be declared in `policy/waivers.yaml`
- each exception requires ADR reference and expiry date
- expired waivers are policy violations

Contract policy:

- external APIs: OpenAPI
- event streams: AsyncAPI + versioned schemas
- AI I/O: Pydantic/JSON Schema validation

Enforcement command:

- `make enforce-section-5-1`

---

## 1. Market Ingestion Service

**Purpose**
- Connect to exchanges/brokers and publish raw events.

**Responsibilities**
- feed handling (WebSocket/REST)
- heartbeat and sequence supervision
- source timestamping
- publish raw events to stream backbone
- persist raw copies to immutable archive

**Consumes**
- exchange feeds
- broker market-data feeds

**Produces**
- `md.raw.ticks.v1`
- `md.raw.trades.v1`
- `md.raw.orderbook.v1`
- `ops.feed_health.v1`

**Technology (mandatory)**
- Rust
- Tokio
- Kafka/Redpanda producer
- object storage client

---

## 2. Market Normalization and Replay Service

**Purpose**
- Normalize raw events into canonical structures and control deterministic replay.

**Responsibilities**
- symbol/time normalization
- deduplication/idempotency
- schema validation
- out-of-order handling
- replay command execution and offset-safe reprocessing

**Consumes**
- `md.raw.*`
- replay commands

**Produces**
- `md.norm.ticks.v1`
- `md.norm.trades.v1`
- `md.norm.orderbook.v1`
- `ops.data_quality.v1`

**Technology (mandatory)**
- Rust
- Kafka/Redpanda consumer groups
- schema validator

---

## 3. Bar Aggregation Service

**Purpose**
- Build OHLCV bars from normalized events.

**Responsibilities**
- bucket aggregation
- session rollover behavior
- bar finalization events
- maintain rolling 90-day `1m` bar coverage for active instruments in `ohlcv_bar` (with support from gap/backfill controller)

**Consumes**
- `md.norm.ticks.v1`
- optional `md.norm.trades.v1`

**Produces**
- `md.bars.1s.v1`
- `md.bars.1m.v1`
- `md.bars.5m.v1`
- `md.bars.15m.v1`

**Storage**
- TimescaleDB/Postgres

**Technology (mandatory)**
- Rust

---

## 4. Gap Detection and Backfill Controller

**Purpose**
- Detect missing data windows and issue deterministic backfill actions.

**Responsibilities**
- gap detection
- backfill command emission
- replay completion monitoring
- startup coverage audit for all active `venue + symbol` pairs to validate full `1m` continuity from `now` to `now - 90 days`
- missing-only backfill orchestration from broker history APIs until startup coverage target is satisfied
- session-aware continuity policy:
  - FX venues (`oanda`, `capital`) evaluate required continuity on trading-session minutes (weekend-closed minutes excluded)
  - crypto venues evaluate required continuity on all minutes (`24/7`)

**Consumes**
- `md.bars.*` (baseline runtime currently consumes `bar.1m`)

**Produces**
- `md.gap_detected.v1`
- `md.backfill_requested.v1`

**Technology (mandatory)**
- Rust

**Mandatory startup behavior**
- At service startup, perform a coverage check against `ohlcv_bar` for every active instrument.
- If any `1m` interval is missing in the last 90 days, enqueue deterministic chunked backfill jobs.
- Mark startup as degraded (not fully ready) until all missing intervals are resolved or an explicit failure state is emitted.

---

## 4.1 Replay Controller

**Purpose**
- Execute `replay.commands` and materialize missing `1m` candles for deterministic backfill ranges.

**Responsibilities**
- consume `replay.commands`
- execute deterministic replay range processing
- rebuild `1m` bars into `ohlcv_bar` from available source ticks
- update `backfill_jobs` lifecycle (`running`/`completed`/`partial`/`failed_no_source_data`)
- update `replay_audit` completion status and moved-count metrics

**Consumes**
- `replay.commands`

**Produces**
- `ohlcv_bar` range updates
- replay/backfill status transitions in Timescale tables

**Technology (mandatory)**
- Rust

**Operational note**
- Replay executes in two stages:
  - deterministic rebuild from retained `raw_tick` ranges,
  - venue-history adapter fallback (`oanda` / `coinbase` / `capital`) when range completeness remains below target.

---

## 5. Structure Engine

**Purpose**
- Implement liquidity-driven market structure deterministically.

**Responsibilities**
- directional liquidity objective
- pullback/extension lifecycle
- inside/outside bar handling
- structure snapshots and confirmations

**Consumes**
- `md.bars.*`

**Produces**
- `structure.snapshot.v1`
- `structure.pullback.v1`
- `structure.minor_confirmed.v1`
- `structure.major_confirmed.v1`

**Technology (mandatory)**
- Rust
- explicit deterministic state machine

**Hard rule**
- single source of truth for structure state

**Baseline status (2026-04-26)**
- deterministic Rust runtime baseline implemented
- replay-safe idempotency via `processed_message_ledger`
- state persisted in `structure_state` per `venue + canonical_symbol + timeframe`

---

## 6. Feature Service

**Purpose**
- Materialize online/offline features.

**Responsibilities**
- feature view definitions
- point-in-time joins
- freshness supervision
- online/offline feature publishing

**Consumes**
- market/structure/portfolio streams

**Produces**
- online feature responses
- `features.snapshot.v1`

**Technology (mandatory)**
- Python (service/jobs)
- Feast

---

## 7. Research Orchestrator

**Purpose**
- Manage dataset creation, labeling, backtests, and experiments.

**Responsibilities**
- replay jobs
- walk-forward validation
- experiment orchestration and tracking

**Technology (mandatory)**
- Python
- MLflow

**Boundary**
- no direct write path into live execution services

---

## 8. Model Training Service

**Purpose**
- Train and register models.

**Responsibilities**
- train/evaluate
- log artifacts/metrics
- register versions/signatures

**Produces**
- model versions
- `ml.model_registered.v1`

**Technology (mandatory)**
- Python
- MLflow

---

## 9. Online Inference Gateway

**Purpose**
- Serve signal/regime/anomaly inference and aggregate decisions.

**Responsibilities**
- scoring and aggregation
- confidence calibration
- response schema enforcement

**Consumes**
- structure snapshots
- online features
- model registry metadata

**Produces**
- `decision.signal_scored.v1`

**Technology (mandatory)**
- Python
- Ray Serve

---

## 10. Risk Engine

**Purpose**
- Enforce hard risk and compliance policies.

**Responsibilities**
- pre-trade checks
- exposure/notional/drawdown controls
- kill-switch enforcement

**Consumes**
- signal events
- portfolio state
- account and venue status
- baseline bootstrap input may use `structure.snapshot.v1` until `decision.signal_scored.v1` is fully online

**Produces**
- `decision.risk_checked.v1`
- `ops.policy_violation.v1`

**Technology (mandatory)**
- Rust

**Hard rule**
- if unavailable, trading fails closed

**Baseline status (2026-04-26)**
- deterministic Rust runtime baseline implemented
- idempotent decision processing via `processed_message_ledger`
- persisted state/log tables: `risk_state`, `risk_decision_log`

---

## 11. Portfolio Engine

**Purpose**
- Maintain live portfolio and strategy state.

**Responsibilities**
- positions, PnL, exposure, cash/margin, allocation state

**Produces**
- `portfolio.snapshot.v1`

**Technology (mandatory)**
- Rust

---

## 12. Execution Gateway (OMS)

**Purpose**
- Convert approved intents into broker/exchange orders.

**Responsibilities**
- create/amend/cancel
- lifecycle state machine
- fill handling and reconciliation
- timeout/retry and slippage telemetry

**Consumes**
- approved intents
- broker/exchange ack/fill streams

**Produces**
- `exec.order_submitted.v1`
- `exec.order_updated.v1`
- `exec.fill_received.v1`
- `exec.reconciliation_issue.v1`

**Technology (mandatory)**
- Rust

**Hard rule**
- this is the only service allowed to place/modify/cancel orders

**Baseline status (2026-04-28)**
- deterministic Rust runtime baseline implemented
- idempotent processing via `processed_message_ledger`
- baseline order lifecycle persisted in `execution_order_journal`
- execution audit trail persisted in `audit_event_log`
- broker adapter baseline implemented for submit/amend/cancel and ack/fill ingest (`exec.order_command.v1`, `broker.execution.ack.v1`)
- command decisions persisted in `execution_command_log`

---

## 13. RAG Indexer

**Purpose**
- Index framework docs/journals/postmortems for retrieval.

**Responsibilities**
- chunking, embedding, metadata tagging, retention/index maintenance

**Technology (mandatory)**
- Python
- pgvector first (Qdrant only if scale requires)

---

## 14. LLM Analyst and Critic Service

**Purpose**
- Produce structured advisory analysis from system state and retrieved context.

**Responsibilities**
- prompt/context assembly
- schema-bound analysis and critique output
- ambiguity/contradiction flags

**Technology (mandatory)**
- Python

**Hard limits**
- cannot create/amend/cancel orders
- cannot override risk
- cannot invent deterministic structure state

---

## 15. Audit and Observability Pipeline

**Purpose**
- Provide full traceability, telemetry, and incident-forensics support.

**Responsibilities**
- end-to-end traces
- metrics/log collection
- decision/risk/execution audit trail persistence

**Baseline status (2026-04-28)**
- persistence contract baseline implemented with `audit_event_log`
- execution journal linkage baseline implemented with `execution_order_journal`
- execution command persistence baseline implemented with `execution_command_log`

**Technology (mandatory)**
- OpenTelemetry
- Prometheus + Grafana
- Loki/Tempo as required by scale/operations

---

## 16. Operator and Charting UI

**Purpose**
- Provide operator controls, charting, and runtime supervision.

**Responsibilities**
- market/portfolio/risk visibility
- controls and operational actions
- incident triage views

**Technology (mandatory)**
- TypeScript frontend (React preferred)
