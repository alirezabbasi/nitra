A production system is **not one model making buy/sell calls**. It is a controlled decision platform with six separate concerns: market data, feature computation, research, signal generation, portfolio/risk control, and execution. The LLM sits on top as a constrained reasoning layer, not as the alpha engine. Your project should be built that way from day one. ([docs.feast.dev][1])

## 1) What you are actually building

You are building an **AI-enabled trading decision platform** with three engines:

1. **Quant engine**
   Generates statistically testable signals from ticks, candles, order book, and derived features.

2. **Execution and risk engine**
   Decides whether a signal is tradable, sizes it, routes the order, monitors fills, and forces exits.

3. **AI reasoning and memory engine**
   Retrieves prior market regimes, past trades, research notes, and system state, then explains or challenges actions under strict policy boundaries.

If you blur these together, you lose debuggability, validation, and control. That is how systems die in production. The point of Feast’s point-in-time joins is exactly to keep training data historically correct, and its serving model is explicitly meant to reduce training-serving skew. MLflow exists to track experiments, enforce model signatures, and register versions instead of letting models drift informally. Ray Serve supports composing separate deployments for model and business-logic stages, which is exactly what you want here. ([docs.feast.dev][1])

## 2) The production target architecture

### A. Market Data Platform

This layer ingests and normalizes:

* tick data
* order book snapshots / deltas
* trades
* candles across multiple timeframes
* reference data
* calendar / session data
* broker and exchange metadata

Use an event-stream backbone for this. Kafka is a practical default because it is built for reading, writing, storing, and processing event streams across many machines. ([Apache Kafka][2])

Store:

* **raw immutable events** in object storage / parquet lake
* **hot analytical time-series** in TimescaleDB
* **normalized embeddings / semantic memory** in pgvector first, Qdrant later only if scale or operational isolation forces it

Timescale is useful here because hypertables, continuous aggregates, and compression policies are built for large time-series workloads. pgvector is practical because it keeps vectors inside Postgres with ACID semantics and native joins, which is the right default for a first production system. Qdrant becomes sensible only when vector search scale and operational needs justify a separate service. ([Tiger Data Docs][3])

### B. Feature Platform

This is where most trading teams get sloppy.

You need a formal feature layer for:

* microstructure features
* volatility and momentum features
* regime features
* pattern features
* execution-state features
* portfolio-state features

Use Feast so the same feature definitions are available offline and online. Its point-in-time correct joins and explicit goal of eliminating training-serving skew are directly relevant to trading research and live inference. ([docs.feast.dev][1])

### C. Research and Model Training Platform

This is where you run:

* dataset creation
* labeling
* walk-forward validation
* feature selection
* hyperparameter tuning
* model comparison
* model packaging

Use MLflow for experiment tracking, model registry, model signatures, and prompt/version control for the LLM layer. The signature requirement matters because it gives you request/response schema discipline for models in deployment. ([MLflow AI Platform][4])

### D. Online Inference and Decision Layer

This must be split into separate services:

* **signal inference service**
* **regime classifier service**
* **portfolio/risk policy service**
* **execution decision service**
* **LLM reasoning service**
* **RAG retrieval service**

Ray Serve is practical here because it supports scalable online inference, composed applications, async workflows, and separate scaling of individual deployments. That is exactly what you need when feature latency, model latency, and LLM latency are different. ([Ray][5])

### E. Execution Platform

This layer owns:

* broker adapters
* pre-trade checks
* order routing
* order state machine
* partial fill handling
* cancel/replace logic
* emergency flatten / kill switch

This engine must remain deterministic. No LLM should be allowed to submit orders directly.

### F. Observability and Governance

You need full telemetry for:

* data freshness
* feature lag
* model latency
* decision latency
* order failures
* slippage
* divergence between simulated and live behavior
* LLM retrieval quality / hallucination incidents

Use OpenTelemetry for traces, metrics, and logs; Prometheus for metric collection and alerting; Alertmanager and/or Grafana Alerting for routing incidents. Keep alerting symptom-based, not vanity-based. Governance should be explicitly risk-based; NIST’s AI RMF is a useful frame for this kind of AI-enabled critical decision system. ([OpenTelemetry][6])

## 3) The module breakdown

This is the modular structure you should use.

### Core platform modules

* `market_ingestion`
* `market_normalization`
* `time_series_storage`
* `feature_store`
* `research_orchestrator`
* `model_training`
* `model_registry`
* `online_inference`
* `rag_memory`
* `risk_engine`
* `portfolio_engine`
* `execution_gateway`
* `trade_journal`
* `monitoring_alerting`
* `governance_audit`

### Strategy modules

Each strategy should be a plugin, not a rewrite:

* `signal_provider`
* `entry_policy`
* `position_sizing_policy`
* `exit_policy`
* `regime_filter`
* `execution_constraints`

### AI modules

* `retrieval_indexer`
* `context_builder`
* `llm_reasoner`
* `decision_critic`
* `explanation_generator`
* `post_trade_reviewer`

This split lets you replace one model or one strategy without destabilizing the rest.

## 4) What the AI should and should not do

### What AI should do

* retrieve similar prior setups
* summarize current market context
* challenge weak signals
* explain proposed entries/exits
* detect policy violations
* assist post-trade review
* help generate research hypotheses

### What AI must not do

* directly place orders
* override hard risk rules
* invent market facts
* infer from incomplete live state without validation
* act as the primary predictive model for ticks/candles

RAG is memory and reasoning support, not the source of edge.

## 5) The real decision pipeline

A live decision should flow like this:

1. market data arrives
2. normalization validates it
3. features update
4. signal model scores opportunity
5. regime filter approves or blocks
6. risk engine checks exposure, liquidity, drawdown, and policy
7. execution policy converts idea into order parameters
8. LLM reviews context and raises warnings only inside a bounded scope
9. deterministic engine decides
10. order routes
11. fills and PnL stream back
12. trade journal and memory update

That is the sequence. Not “LLM reads candles and decides.”

## 6) The data model you need from the start

At minimum define these entities:

* `raw_tick`
* `book_event`
* `trade_print`
* `ohlcv_bar`
* `instrument`
* `session_calendar`
* `feature_snapshot`
* `signal_score`
* `regime_state`
* `risk_state`
* `portfolio_position`
* `order_intent`
* `broker_order`
* `execution_fill`
* `trade_decision`
* `trade_outcome`
* `research_run`
* `model_version`
* `prompt_version`
* `retrieved_context`
* `audit_event`

If this schema is weak, your system will become untraceable.

## 7) The stack I would choose

For a practical open-source first build:

### Data and storage

* Kafka for event streaming ([Apache Kafka][2])
* TimescaleDB for time-series market data and aggregates ([Tiger Data Docs][3])
* Postgres + pgvector for metadata, audit, and initial vector memory ([GitHub][7])
* Object storage + Parquet for raw historical data lake

### ML / AI platform

* Feast for online/offline feature parity ([docs.feast.dev][1])
* MLflow for tracking, registry, signatures, prompt registry ([MLflow AI Platform][4])
* Ray Serve for live inference services and orchestration ([Ray][5])

### RAG

* pgvector first
* Qdrant later if retrieval scale, HA, or isolated vector ops become real needs ([GitHub][7])

### Observability

* OpenTelemetry + Prometheus + Alertmanager + Grafana ([OpenTelemetry][6])

This stack is boring enough to run and strong enough to scale.

## 8) Project phases

### Phase 0 — Constraints and design

Deliverables:

* trading venue and asset-class scope
* latency target
* holding-period target
* strategy family target
* risk limits
* explainability requirements
* audit requirements
* paper-trading acceptance criteria

Do not skip this. A scalping architecture and a swing-trading architecture are not the same system.

### Phase 1 — Data foundation

Build:

* market data connectors
* normalization pipeline
* immutable raw storage
* Timescale schema
* continuous aggregates
* quality checks
* replay capability

Exit criteria:

* can replay one month of historical data accurately
* can reconstruct candles from raw events
* freshness and gap alerts are working

### Phase 2 — Research foundation

Build:

* dataset builder
* feature definitions in Feast
* labeling framework
* baseline backtesting
* walk-forward validation
* MLflow tracking and registry

Exit criteria:

* one reproducible research pipeline
* one benchmark strategy
* one documented baseline model that beats the benchmark net of costs in research only

### Phase 3 — Live inference foundation

Build:

* online feature serving
* signal scoring API
* risk policy engine
* order simulator
* trade journal
* observability

Exit criteria:

* end-to-end paper trading
* no manual intervention required
* all decisions traceable from feature snapshot to order outcome

### Phase 4 — AI and RAG layer

Build:

* memory ingestion from trade journal, postmortems, research notes
* retrieval service
* context builder
* LLM reviewer / critic
* bounded explanation templates
* prompt versioning and evaluation

Exit criteria:

* AI can explain a decision using retrieved evidence
* AI cannot bypass hard rules
* hallucination tests and retrieval-eval tests pass internally

### Phase 5 — Broker integration and sandbox live

Build:

* broker adapter
* pre-trade guardrails
* kill switch
* slippage monitor
* exposure controls
* emergency flatten workflow

Exit criteria:

* stable paper/live shadow mode
* bounded operational incidents
* risk controls proven in failure drills

### Phase 6 — Limited capital production

Start with:

* one instrument group
* one strategy
* tiny capital
* fixed risk caps
* human review on major anomalies

Scale only after statistically meaningful live results.

## 9) MVP definition

Your MVP should be brutally narrow:

* one market
* one broker
* one strategy family
* one timeframe family
* one feature set
* one signal model
* one deterministic risk engine
* one LLM reviewer
* paper trading first

Anything broader is ego, not engineering.

## 10) Team split

Minimum serious team:

* data engineer
* quant / ML engineer
* backend / platform engineer
* execution / integration engineer
* DevOps / SRE
* product owner with trading discipline

If one person is doing all of this, scope must shrink hard.

## 11) Success metrics

Track these from day one:

* data freshness lag
* feature computation latency
* model inference latency
* decision latency
* order reject rate
* fill rate
* slippage vs benchmark
* max drawdown
* hit rate by regime
* average adverse excursion
* average favorable excursion
* live vs backtest divergence
* retrieval precision for RAG
* LLM warning usefulness rate
* policy violation count

If you do not measure these, you do not have a production system. You have a hobby.

## 12) Biggest failure modes

These will kill the project first:

* training-serving skew
* lookahead leakage
* overfit backtests
* weak cost/slippage modeling
* no deterministic risk boundary
* letting the LLM “decide”
* no replayable audit trail
* too many markets/strategies too early
* mixing research and production code paths
* weak incident response and alerting

The architecture above is designed specifically to block those failures. Feast, MLflow signatures/registry, Ray Serve composition, and proper observability are not decoration; they are there to prevent exactly these operational mistakes. ([docs.feast.dev][1])

## 13) The exact next move

You should lock this into four workstreams immediately:

1. **Data platform**
   Define schemas, ingestion contracts, replay design, Timescale layout.

2. **Research platform**
   Define feature catalog, label definitions, validation protocol, MLflow conventions.

3. **Execution and risk**
   Define order state machine, hard risk rules, broker abstraction, kill-switch logic.

4. **AI layer**
   Define what context gets embedded, what prompts are versioned, what the LLM is allowed to output, and what it is forbidden to do.

That is the real-world structure.

[1]: https://docs.feast.dev/getting-started/concepts/point-in-time-joins?utm_source=chatgpt.com "Point-in-time joins | Feast: the Open Source Feature Store"
[2]: https://kafka.apache.org/documentation/?utm_source=chatgpt.com "Introduction | Apache Kafka"
[3]: https://docs.timescale.com/getting-started/latest/add-data/?__hsfp=3006156910&__hssc=231067136.3.1766707200261&__hstc=231067136.73bd3bee6fa385653ecd7c9674ba06f0.1766707200258.1766707200259.1766707200260.1&utm_source=chatgpt.com "Tiger Cloud essentials | Tiger Data Docs"
[4]: https://mlflow.org/?utm_source=chatgpt.com "MLflow - Open Source AI Platform for Agents, LLMs & Models"
[5]: https://docs.ray.io/en/latest/serve/index.html?utm_source=chatgpt.com "Ray Serve: Scalable and Programmable Serving — Ray 2.55.0"
[6]: https://opentelemetry.io/docs/what-is-opentelemetry/?utm_source=chatgpt.com "What is OpenTelemetry?"
[7]: https://github.com/pgvector/pgvector?utm_source=chatgpt.com "pgvector/pgvector: Open-source vector similarity search for ..."
