# BarsFP Revamp Epic Roadmap

This plan converts `barflow` into `barsfp` on the new target stack.

Related:
- `migration-map-from-barflow.md`
- `step-by-step-commit-plan.md`
- `epics/EPIC-XX/README.md` per epic

## Epic 0: Program Setup and Contracts Lock

Outcomes:
- Scope lock, success criteria, architecture contracts frozen.
- Repo, coding standards, docs baseline, ADR process online.

## Epic 1: Monorepo and Rust Workspace Foundation

Outcomes:
- Rust workspace with service crates and shared domain crate.
- Local dev stack baseline (Redpanda, Timescale, ClickHouse, MinIO, Grafana).

## Epic 2: Redpanda Backbone and Message Contracts

Outcomes:
- Topic registry and schema versioning.
- Producer/consumer reliability policies (retry, DLQ, replay).

## Epic 3: Connector Ingestion (Broker 1 End-to-End)

Outcomes:
- Rust connector for first broker.
- Raw stream durability and health telemetry.

## Epic 4: Canonical Normalization + Symbol Registry

Outcomes:
- Canonical event model implemented.
- Symbol/session/canonical mapping service.

## Epic 5: Deterministic Bar Engine + Hot Store

Outcomes:
- 1s/1m bars from canonical events.
- TimescaleDB schema, hypertables, aggregates, 90-day retention controls.

## Epic 6: Gap Engine + Precision Backfill + Replay

Outcomes:
- Internal/tail gap detection.
- Missing-only backfill and deterministic rebuild pipeline.

## Epic 7: Lakehouse Archive (MinIO) + Cold Path Loading

Outcomes:
- Immutable Parquet archive with manifests/checkpoints.
- Verified hot->lake transitions.

## Epic 8: ClickHouse Analytics Warehouse

Outcomes:
- Historical bar/event analytical model.
- Operational APIs split hot vs cold query paths.

## Epic 9: Risk Gateway + OMS + Reconciliation

Outcomes:
- Pre/post-trade risk controls.
- Order state machine, fill handling, reconciliation loops.

## Epic 10: Observability and SLO Enforcement

Outcomes:
- Prometheus/Loki/Tempo instrumentation.
- Grafana dashboards and actionable alert policies.

## Epic 11: Paper Rollout, Micro-Live Gate, and Closure

Outcomes:
- Paper stability evidence.
- Micro-live checklist and rollback validation.
- Final sign-off and known-limits register.

## Epic 12: Delivery Integrity and Idempotency Hardening

Outcomes:
- Manual commit integrity strategy and deterministic rollback points.
- Idempotent processing guarantees and replay-safe side effects.

## Epic 13: Durable Stateful Stream Engines

Outcomes:
- Durable stream checkpoints and deterministic restart behavior.
- Stateful processor recovery without output drift.

## Epic 14: Contract and Allocation Optimization

Outcomes:
- Typed contract improvements and reduced serialization overhead.
- Allocation profile baseline and throughput/latency gains.

## Epic 15: Async I/O and Backpressure Reliability

Outcomes:
- Blocking I/O isolation from async runtimes.
- Batching and bounded backpressure controls for ingestion/archive paths.

## Epic 16: Query and Storage Performance Tuning

Outcomes:
- Hot/cold path query optimization and storage policy hardening.
- Latency SLO compliance on operational and analytical queries.

## Epic 17: Unified Telemetry Correlation and SLO Diagnostics

Outcomes:
- Unified metrics/traces/log correlation IDs and contracts.
- Faster incident detection and root-cause isolation workflows.

## Epic 18: Production Runtime Security Hardening

Outcomes:
- Secrets, network policy, authn/authz, and resource hardening baselines.
- Signed production readiness security checklist.

## Epic 19: Performance Regression Gates in CI

Outcomes:
- Benchmark/load/soak/chaos execution suites.
- CI performance budgets and regression blockers.

## Epic 20: Disaster Recovery and Business Continuity

Outcomes:
- Automated backup/restore workflows.
- DR drill evidence aligned to approved RPO/RTO objectives.

## Epic 21: Market Event Canonical Persistence

Outcomes:
- First-class persistence for `raw_tick`, `book_event`, `trade_print`.
- Replay-safe and deduplicated multi-venue market event history.

## Epic 22: Reference Data and Trading Session Model

Outcomes:
- First-class `instrument` and `session_calendar` entities.
- Session-aware validation boundaries in canonical ingestion.

## Epic 23: Feature and Signal State Backbone

Outcomes:
- Durable `feature_snapshot`, `signal_score`, and `regime_state` entities.
- Traceable feature-to-signal lineage in live/runtime decisions.

## Epic 24: Portfolio and Risk State Model

Outcomes:
- Durable `risk_state` and `portfolio_position` entities.
- Reproducible risk decisions backed by persisted state.

## Epic 25: Decision-to-Execution Lineage Model

Outcomes:
- First-class `order_intent`, `broker_order`, and `trade_decision` linkage.
- Full traceability from decision policy to execution fills.

## Epic 26: Trade Outcome and Journal Completeness

Outcomes:
- Durable `trade_outcome` entity and lifecycle.
- Deterministic close-trade attribution (PnL, slippage, costs).

## Epic 27: Research, Model, and Prompt Governance

Outcomes:
- First-class `research_run`, `model_version`, `prompt_version` entities.
- Runtime linkage from production decisions to governed model/prompt versions.

## Epic 28: Retrieval Context and AI Audit Trail

Outcomes:
- Durable `retrieved_context` and `audit_event` entities.
- End-to-end AI decision evidence for policy/compliance review.

## Epic 29: Contract Enforcement and Migration Hardening

Outcomes:
- Compatibility gates for contracts/schema/topic evolution.
- CI-enforced migration safety and breaking-change controls.
