# Production HLD — AI-Enabled Trading System

## 1. Purpose

This document defines the **High-Level Design (HLD)** for a production-grade, AI-enabled trading platform that analyzes market data, derives structural state, evaluates opportunities, manages risk, and executes trades under strict operational controls.

The system is designed around one non-negotiable principle:

**Deterministic trading logic, risk enforcement, and execution control must remain separate from LLM-based reasoning.**

The LLM layer is an analyst and critic, not the execution authority.

---

## 2. Design Principles

1. **Event-driven first**
   - Market systems are streams, not request/response applications.
   - Kafka is used as the backbone for durable event ingestion, storage, and processing. citeturn118289search0turn118289search8

2. **Deterministic core, probabilistic edge**
   - Structural parsing, risk limits, and order state transitions are deterministic.
   - ML/LLM components are advisory or scoring layers.

3. **Separation of concerns**
   - Research, online inference, execution, AI reasoning, and observability are isolated into independent services.

4. **Training/serving parity**
   - Feature definitions must remain consistent offline and online to avoid silent model failure.
   - Feast is explicitly intended to solve training-serving skew and complex point-in-time joins. citeturn118289search1

5. **Schema-governed ML**
   - Every model and LLM-facing interface must use explicit signatures/contracts.
   - MLflow model signatures define expected input/output schemas and help validate deployment requests. citeturn118289search2turn118289search10

6. **Composable serving**
   - Inference pipelines should be deployable as composed applications with independently scalable parts.
   - Ray Serve supports online inference APIs, model composition, and separate scaling of deployments. citeturn118289search3turn118289search11turn118289search14

7. **Full observability**
   - OpenTelemetry provides vendor-neutral telemetry collection for traces, metrics, and logs. citeturn914213search1turn914213search7turn914213search10

8. **Cloud-native operations**
   - Kubernetes is used for deployment, scaling, and management of containerized workloads, with Deployments for stateless apps and StatefulSets where needed. citeturn914213search8turn914213search23turn914213search11

---

## 3. Scope

### Included
- Market data ingestion and replay
- Candle/tick/order book normalization
- Deterministic market-structure engine
- Feature engineering and feature serving
- Research and backtesting platform
- Online signal scoring
- Portfolio and risk management
- Broker/exchange execution gateway
- LLM/RAG analyst layer
- Observability, audit, and governance
- Paper trading, shadow mode, and limited live rollout

### Excluded
- Retail UI details
- Broker-specific API minutiae
- Strategy alpha details
- Final low-level DB migration scripts
- Final OpenAPI / AsyncAPI schema definitions

### Domain Deep-Dive References

- Ingestion domain implementation and operational design pack:
  - `docs/design/ingestion/`
  - `docs/design/ingestion/ruleset.md`

---

## 4. System Context

### External Inputs
- Exchange market data feeds
- Broker/exchange order APIs
- Reference data providers
- Trading calendars / session metadata
- News or macro feeds (optional)

### Internal Consumers
- Research users
- Quant/ML pipelines
- Strategy services
- Portfolio/risk services
- Operations / SRE teams
- Analyst/monitoring dashboards

### External Outputs
- Orders
- Cancellations / modifications
- Trade journals
- Audit logs
- Alerts / incidents
- Research datasets
- AI-generated analysis summaries

---

## 5. High-Level Architecture

```text
                    +----------------------+
                    |  Exchange / Broker   |
                    |  Feeds + APIs        |
                    +----------+-----------+
                               |
                               v
+----------------+   +----------------------+   +----------------------+
| Raw Data Lake  |<--| Market Ingestion     |-->| Kafka Event Backbone |
| Object Storage |   | Connectors           |   | Topics / Streams     |
+----------------+   +----------------------+   +----------+-----------+
                                                           |
                                                           v
                                      +--------------------------------------+
                                      | Market Normalization & Replay        |
                                      | Tick/Trade/Book Validation + Bars    |
                                      +----------------+---------------------+
                                                           |
                              +----------------------------+----------------------------+
                              |                             |                           |
                              v                             v                           v
               +--------------------------+   +-------------------------+   +----------------------+
               | Deterministic Structure   |   | Time-Series Storage     |   | Feature Platform     |
               | Engine (Rust)            |   | TimescaleDB             |   | Feast                |
               +-------------+------------+   +------------+------------+   +-----------+----------+
                             |                             |                            |
                             +-----------------------------+----------------------------+
                                                           |
                                                           v
                                        +----------------------------------------------+
                                        | Research / Backtesting / Dataset Builder     |
                                        | MLflow Tracking + Registry                   |
                                        +--------------------+-------------------------+
                                                             |
                                                             v
                                    +------------------------------------------------------+
                                    | Online Inference Layer                               |
                                    | Signal Model / Regime Model / Decision Aggregation   |
                                    | Ray Serve                                            |
                                    +----------------------+-------------------------------+
                                                           |
                              +----------------------------+----------------------------+
                              |                             |                           |
                              v                             v                           v
                +-------------------------+   +--------------------------+  +---------------------------+
                | Risk Engine             |   | Portfolio Engine         |  | RAG + LLM Analyst Layer  |
                | Hard Limits / Policies  |   | Exposure / PnL / Limits  |  | Context + Critique        |
                +------------+------------+   +------------+-------------+  +-------------+-------------+
                             |                             |                              |
                             +-----------------------------+------------------------------+
                                                           |
                                                           v
                                          +----------------------------------+
                                          | Execution Gateway                |
                                          | Order State Machine / Broker I/O |
                                          +----------------+-----------------+
                                                           |
                                                           v
                                          +----------------------------------+
                                          | Audit / Journaling / Monitoring  |
                                          | OpenTelemetry + Metrics + Alerts |
                                          +----------------------------------+
```

### 5.1 Enforced Technology Allocation Policy

This policy is mandatory for production runtime architecture and is governed by ADR-0001 in `docs/design/ARCHITECTURE_DECISIONS.md`.

**Deterministic core: Rust-only**
- market ingestion connectors
- market normalization and replay
- bar aggregation, gap detection, backfill controller
- structure engine
- risk engine
- portfolio engine
- execution gateway and OMS state machine

**Probabilistic/ML/AI layer: Python-only**
- research and backtesting
- feature engineering jobs
- online model inference services
- RAG and LLM analyst/critic services

**Contracts and interoperability**
- external APIs: OpenAPI
- event streams: AsyncAPI + versioned schemas
- AI I/O: Pydantic/JSON Schema validation at runtime

**Platform standards**
- streaming backbone: Kafka/Redpanda
- hot store: TimescaleDB/Postgres
- raw archive: S3/MinIO + Parquet
- vector memory: pgvector first (Qdrant only if scale requires)
- inference serving: Ray Serve
- observability: OpenTelemetry + Prometheus + Grafana (Loki/Tempo as needed)
- UI: TypeScript/React (or lightweight TypeScript frontend)

**Control boundaries (non-negotiable)**
- LLM layer is advisory only
- only deterministic Rust execution path may place/modify/cancel orders
- if AI services fail, deterministic path remains operable
- if risk/execution integrity is uncertain, system fails closed

**Anti-duplication rule**
- one runtime language per layer:
  - Rust for deterministic core
  - Python for probabilistic/AI layer
  - TypeScript for UI
- no parallel Python/Rust implementation of the same production core component

**Waiver and migration controls**
- temporary non-compliance requires ADR-linked waiver with explicit expiry
- migration state model:
  - `compliant`
  - `non_compliant_migrating`
  - `blocked` (no net-new feature scope while non-compliant)
- enforcement gates must pass:
  - `make enforce-section-5-1`
  - includes technology and contract policy checks

---

## 6. Layered Design

### 6.1 Market Data Layer
Responsible for collecting, validating, and persisting all inbound market events.

**Components**
- exchange feed adapters
- broker adapters
- reference data adapters
- session/calendar service
- raw event archiver

**Responsibilities**
- subscribe to tick, trade, and order book feeds
- validate transport-level integrity
- stamp source metadata and ingest timestamp
- publish immutable events to Kafka
- persist raw events to object storage for replay

Kafka is designed to read, write, store, and process event streams durably across many machines, which fits market-data ingestion and replay requirements. citeturn118289search8turn118289search15

### 6.2 Normalization and Replay Layer
Responsible for transforming raw streams into canonical internal representations.

**Components**
- tick normalizer
- trade normalizer
- order book normalizer
- OHLCV aggregator
- gap detector
- replay controller

**Responsibilities**
- normalize symbol identifiers
- normalize timestamps and sequence ordering
- reject or quarantine malformed events
- aggregate ticks into bars
- support deterministic historical replay into downstream services
- enforce startup historical coverage for active instruments: on service start, verify `ohlcv_bar` has a complete rolling 90-day window of `1m` bars per active `venue + symbol`; if gaps exist, trigger missing-only broker backfill until coverage is complete

**Coverage policy (mandatory)**
- charting operational baseline is always `now` back to `now - 90 days` on `1m`
- the system must not rely on manual operator action to repair missing historical windows after restart
- startup coverage check/backfill runs before normal steady-state status is reported healthy

### 6.3 Deterministic Market Structure Layer
Responsible for applying the liquidity-driven market-structure framework in code.

**Technology bias**
- Rust service for correctness, performance, and deterministic state handling

**Responsibilities**
- consume normalized bars/ticks
- track liquidity state
- detect pullbacks and extensions
- apply inside-bar / outside-bar reference rules
- maintain minor structure archive
- detect major structure activation
- emit structure-state snapshots

**Boundary**
- this service is authoritative for structural state
- the LLM is not allowed to reinterpret hard rules

### 6.4 Time-Series Storage Layer
Responsible for hot analytical storage.

**Primary store**
- TimescaleDB / PostgreSQL

**Responsibilities**
- store normalized time-series data
- store feature snapshots
- support analytical queries
- support retention, compression, and continuous aggregates

Timescale documentation explicitly highlights hypertables, continuous aggregates, and compression-aware workflows for time-series use cases. citeturn914213search9turn914213search0turn914213search6

### 6.5 Feature Platform
Responsible for producing reusable online and offline features.

**Primary technology**
- Feast

**Responsibilities**
- define feature views
- perform point-in-time correct joins
- serve online features for inference
- export offline datasets for research
- prevent offline/online skew

Feast’s documentation explicitly calls out training-serving skew and point-in-time joins as key problems it solves. citeturn118289search1

### 6.6 Research and Experimentation Layer
Responsible for all non-production strategy and model development.

**Components**
- dataset builder
- backtest engine
- walk-forward validator
- labeling framework
- experiment runner
- model registry interface

**Primary technology**
- MLflow

**Responsibilities**
- track experiments
- register model versions
- enforce model signatures
- compare runs and metrics
- support classic ML and GenAI evaluation paths

MLflow documents model signatures as explicit input/output contracts and also provides evaluation support, including GenAI evaluation flows. citeturn118289search2turn118289search16

### 6.7 Online Inference and Decision Layer
Responsible for serving models in production and assembling trade decisions.

**Primary technology**
- Ray Serve

**Responsibilities**
- host signal scoring services
- host regime classifier services
- host optional anomaly models
- compose business logic and model calls
- independently scale model-serving components

Ray Serve supports composing multiple deployments into one application and independently scaling them to avoid bottlenecks. citeturn118289search7turn118289search11turn118289search17

### 6.8 Risk and Portfolio Control Layer
Responsible for hard operational safety.

**Components**
- pre-trade risk checks
- exposure tracker
- max drawdown controls
- margin/liquidity checks
- position sizing rules
- kill switch
- portfolio state service

**Responsibilities**
- reject trades violating hard rules
- cap strategy-level and portfolio-level exposure
- track realized/unrealized PnL
- enforce concentration and loss limits
- trigger circuit breakers

**Critical rule**
- this layer is authoritative over any signal or AI recommendation

### 6.9 Execution Layer
Responsible for all outbound trading actions.

**Components**
- execution gateway
- broker adapters
- order router
- order state machine
- fill reconciler
- retry / timeout logic

**Responsibilities**
- place, amend, cancel orders
- track order lifecycle
- handle partial fills and rejects
- reconcile broker state and internal state
- emit execution events for audit and analysis

**Order states**
- created
- validated
- submitted
- acknowledged
- partially_filled
- filled
- canceled
- rejected
- expired
- reconciliation_error

### 6.10 AI Reasoning and Memory Layer
Responsible for contextual interpretation, critique, and explanation.

**Components**
- retrieval service
- embedding/indexing pipeline
- prompt/context builder
- LLM analyst
- LLM critic / reviewer
- explanation generator

**Responsibilities**
- retrieve relevant framework rules
- retrieve similar prior scenarios
- analyze deterministic structure-state snapshots
- produce structured summaries
- flag ambiguity or contradictions
- support post-trade review and incident analysis

**Strict limitations**
- cannot directly send orders
- cannot override risk rules
- cannot invent structure states
- must output schema-constrained results

### 6.11 Observability, Audit, and Governance Layer
Responsible for operational visibility and traceability.

**Primary standards / tools**
- OpenTelemetry for traces/metrics/logs
- Prometheus-compatible metric collection
- Grafana dashboards
- alert routing
- audit event storage

OpenTelemetry is explicitly designed as an observability framework for generation, export, and collection of traces, metrics, and logs. citeturn914213search1turn914213search7turn914213search10

**Responsibilities**
- end-to-end trace of every decision path
- latency breakdown by service
- model inference telemetry
- collector health telemetry
- auditability for every order decision
- policy-violation alerting

---

## 7. Deployment Topology

### Compute Platform
- Kubernetes cluster for core services
- GPU node pool only for model-serving / LLM services as needed
- CPU node pools for ingestion, normalization, risk, and execution services
- isolated namespaces by environment: dev, research, staging, prod

Kubernetes provides Deployments for stateless workloads and supports horizontal scaling of workloads such as Deployments and StatefulSets. citeturn914213search8turn914213search13turn914213search5

### Workload Placement
**Stateless Deployments**
- API gateway
- inference APIs
- LLM services
- context builder
- monitoring APIs

**Stateful / persistent services**
- Kafka cluster
- PostgreSQL / TimescaleDB
- object storage gateway if self-hosted
- vector store if separated from Postgres later

**Batch / job workloads**
- historical backfills
- feature recomputation
- model training
- evaluation jobs
- replay jobs
- migration jobs

Kubernetes guidance distinguishes long-running applications from finite jobs; use Deployments for always-on services and Jobs for batch tasks. citeturn914213search21

---

## 8. Environment Model

### Development
- mocked feeds
- local object storage
- single-node Kafka
- local PostgreSQL
- optional lightweight model serving

### Staging / Paper Trading
- real market data
- simulated order routing
- replay plus live-feed comparison
- full observability
- feature parity checks

### Production
- real feeds
- real brokers
- HA Kafka
- HA PostgreSQL / TimescaleDB
- dedicated risk and execution services
- strict secret management
- incident response integration

---

## 9. Data Flow

### Inbound Market Flow
1. exchange/broker emits market event
2. ingestion adapter receives event
3. event is stamped, validated, and published to Kafka
4. raw copy is archived to object storage
5. normalizer consumes raw topic
6. normalized event and bars are emitted
7. structure engine consumes normalized events
8. structure state snapshot is emitted
9. feature pipelines compute or update feature values
10. online inference consumes structure + feature state
11. risk and portfolio engines evaluate tradability
12. execution gateway acts if approved
13. resulting order/fill events return to Kafka and storage
14. audit and observability pipelines persist complete trace

### AI Analysis Flow
1. structure snapshot arrives
2. retrieval service fetches rule fragments and similar prior cases
3. prompt builder assembles structured context
4. LLM returns schema-bound interpretation
5. critic service validates policy compliance
6. result is stored as advisory context only

---

## 10. Security and Control Boundaries

- All inbound exchange and broker data is untrusted until validated and normalized.
- Model outputs are advisory until validated against schema, policy, and runtime constraints.
- Only the deterministic execution service may place or modify orders.
- Operators may disable strategies, brokers, venues, or the entire system via kill-switch controls.

**Control requirements**
- service-to-service authentication
- secret management
- immutable audit logs
- role-based access control
- environment segregation
- approval gating for production model promotion

---

## 11. High Availability Strategy

### Must be highly available
- Kafka
- TimescaleDB / PostgreSQL
- execution gateway
- risk engine
- market ingestion
- observability pipeline

### Can degrade gracefully
- LLM analyst
- historical retrieval enrichment
- non-critical dashboards
- research services

### Failure posture
- if AI services fail: system continues with deterministic logic only
- if research services fail: production continues
- if risk engine fails: trading must fail closed
- if execution reconciliation fails: trading must pause on affected venue/broker

---

## 12. Scaling Strategy

### Horizontal scaling candidates
- ingestion adapters by venue/symbol partition
- normalization workers
- feature serving
- inference services
- retrieval services
- read-only APIs

### Vertical / specialized scaling candidates
- GPU-backed LLM serving
- memory-heavy backtests
- large feature-materialization jobs

### Stateful scaling
- Kafka partitions
- DB read replicas where appropriate
- object storage tiering

Kubernetes supports workload management and autoscaling patterns for production applications. citeturn914213search5turn914213search13turn914213search15

---

## 13. Core Data Stores

### Object Storage
Purpose:
- immutable raw event archive
- backtest input sets
- model artifacts
- replay source

### PostgreSQL / TimescaleDB
Purpose:
- normalized time-series
- structure snapshots
- feature snapshots
- orders, fills, positions
- audit references
- operational metadata

### Vector / semantic store
Initial recommendation:
- pgvector inside Postgres first

Purpose:
- framework docs
- prior annotated scenarios
- post-trade journals
- retrieval support for LLM context

---

## 14. Key Non-Functional Requirements

### Reliability
- fail closed on risk/control uncertainty
- recoverable from feed interruptions
- replayable after incidents

### Performance
Indicative latency budgets:
- ingest validation: < 10 ms
- normalization/structure update: < 20 ms
- feature retrieval: < 20 ms
- inference scoring: < 30 ms
- risk decision: < 10 ms
- execution dispatch: venue-dependent, target < 50 ms internal overhead

### Auditability
- every decision linked to source market state, feature snapshot, model version, policy version, execution result, and optional AI advisory context

### Maintainability
- bounded service responsibilities
- explicit schemas
- versioned contracts
- replay-driven debugging

---

## 15. Release Model

### Release stages
1. research-only
2. backtest-approved
3. replay-approved
4. paper-trading
5. shadow live
6. limited-capital live
7. scaled production

### Promotion gates
- data-quality checks pass
- no schema violations
- model registry approval complete
- inference contract validated
- risk-policy regression tests pass
- replay parity within tolerance
- incident rollback path tested

---

## 16. Why This Architecture

This design avoids the most common failure pattern in AI trading projects:

**using an LLM as the trader instead of as a controlled analytical subsystem.**

It instead places:
- Kafka at the event backbone for durable streaming, storage, and processing of market events, citeturn118289search0turn118289search8
- Feast at the feature boundary to keep offline and online features aligned, citeturn118289search1
- MLflow at the experiment and registry boundary to enforce model contracts, citeturn118289search2turn118289search10
- Ray Serve at the inference boundary to compose and scale model-serving paths, citeturn118289search3turn118289search11
- OpenTelemetry at the observability boundary for traces, metrics, and logs, citeturn914213search1turn914213search10
- Kubernetes at the runtime boundary for automated deployment, scaling, and workload management, citeturn914213search23turn914213search8
- TimescaleDB at the time-series boundary for hypertables, continuous aggregates, and compression-aware storage patterns. citeturn914213search9turn914213search0

That is a production system shape.
Not a toy bot.
Not a prompt chain with delusions of grandeur.

---

## 17. Next Design Artifacts

1. service catalog
2. repository structure
3. API contracts (OpenAPI)
4. event contracts (AsyncAPI)
5. database schema v1
6. state-machine specifications
7. deployment topology diagrams
8. SLOs / alert matrix
9. security model
10. LLD for each service domain
