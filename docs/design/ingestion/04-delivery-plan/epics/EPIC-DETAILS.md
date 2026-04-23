# Epic Details and Acceptance Gates

## Epic 0
- Deliverables: charter, ADR-000, environment model, DoD/DoR templates.
- Exit gate: written sign-off of target architecture and constraints.

## Epic 1
- Deliverables: Rust workspace, CI skeleton, local compose stack.
- Exit gate: all core services compile; local stack boots cleanly.

## Epic 2
- Deliverables: Redpanda topics, schema registry policy, retry/DLQ/replay contracts.
- Exit gate: replay tests show no silent loss under injected failures.

## Epic 3
- Deliverables: broker-1 connector, reconnect policy, raw stream metrics.
- Exit gate: stable session ingest and heartbeat for 5 consecutive days (paper).

## Epic 4
- Deliverables: normalization pipeline, canonical validator, symbol registry.
- Exit gate: canonical payload pass rate >= 99.99% on valid source traffic.

## Epic 5
- Deliverables: deterministic 1s/1m aggregation, Timescale schema, retention job.
- Exit gate: rebuild determinism proven on replay sample windows.

## Epic 6
- Deliverables: coverage tracker, missing-only backfill, gap lifecycle table.
- Exit gate: internal + tail gaps repaired with no overfetch in QA drills.

## Epic 7
- Deliverables: Parquet archive writer, manifest/checksum, idempotent reruns.
- Exit gate: row-count and checksum reconciliation passes on archival jobs.

## Epic 8
- Deliverables: ClickHouse model + ETL from lake, cold query APIs.
- Exit gate: heavy historical analytics offloaded from Timescale.

## Epic 9
- Deliverables: risk gateway, OMS, fills, reconciliation, kill switch.
- Exit gate: no order path can bypass risk checks.

## Epic 10
- Deliverables: dashboards, SLO metrics, alerts, incident drill runbooks.
- Exit gate: on-call drill executed successfully with evidence.

## Epic 11
- Deliverables: paper report, micro-live rollout controls, closure audit.
- Exit gate: all final QA checks green and signed by product/risk/ops owners.

## Epic 12
- Deliverables: manual commit strategy, idempotency keys/store, replay-safe side effects.
- Exit gate: failure-injection replay shows no silent loss and no duplicate side effects.

## Epic 13
- Deliverables: durable state checkpoints for stream engines and deterministic restart recovery.
- Exit gate: controlled restart resumes without state drift or missed bar/gap windows.

## Epic 14
- Deliverables: typed event contracts, reduced serde overhead, allocation profile baseline.
- Exit gate: measured throughput/latency improvement under the same synthetic load.

## Epic 15
- Deliverables: async-safe blocking I/O isolation, batch ingest tuning, bounded backpressure controls.
- Exit gate: archival/load jobs meet throughput SLO without starving async executors.

## Epic 16
- Deliverables: hot/cold query tuning, retention/compression policy hardening, storage-level indexes/partitions.
- Exit gate: P95/P99 query latency targets met for both operational and analytical paths.

## Epic 17
- Deliverables: standardized metrics/traces/logs, correlation IDs, SLO dashboards and burn-rate alerts.
- Exit gate: incident drill demonstrates fast detection and root-cause isolation from telemetry.

## Epic 18
- Deliverables: production runtime hardening (secrets, network policy, authn/authz, resource limits).
- Exit gate: security and platform readiness checklist fully signed off.

## Epic 19
- Deliverables: benchmark suite, load/soak/chaos tests, performance regression gates in CI.
- Exit gate: release candidate passes performance budget and resilience test matrix.

## Epic 20
- Deliverables: backup/restore automation, DR runbooks, RPO/RTO validation evidence.
- Exit gate: disaster recovery drill succeeds within approved business thresholds.

## Epic 21
- Deliverables: `raw_tick`/`book_event`/`trade_print` schema, multi-venue persistence writes, replay-safe dedupe checks.
- Exit gate: canonical market micro-events persist across venues with replay determinism and no silent loss.

## Epic 22
- Deliverables: `instrument` and `session_calendar` schema plus loaders, validation guards in normalization pipeline.
- Exit gate: canonical ingest blocks invalid instrument/session traffic and records rejection evidence.

## Epic 23
- Deliverables: `feature_snapshot`, `signal_score`, and `regime_state` entities with lineage keys.
- Exit gate: every live signal resolves to persisted features and regime state.

## Epic 24
- Deliverables: `risk_state` and `portfolio_position` persistence and update workflows.
- Exit gate: risk gateway decisions are reproducible from durable state snapshots.

## Epic 25
- Deliverables: `order_intent`, `broker_order`, `trade_decision` linkage model with correlation IDs.
- Exit gate: any execution fill can be traced back to originating decision and policy checks.

## Epic 26
- Deliverables: `trade_outcome` schema, lifecycle logic, and journal views.
- Exit gate: each closed trade has deterministic outcome attribution and auditable records.

## Epic 27
- Deliverables: `research_run`, `model_version`, and `prompt_version` governance model and promotion workflow.
- Exit gate: production decisions map to exact research/model/prompt versions with rollback trace.

## Epic 28
- Deliverables: `retrieved_context` and `audit_event` persistence, AI policy event logging contracts.
- Exit gate: AI-assisted decisions retain retrieval evidence and policy-audit history end-to-end.

## Epic 29
- Deliverables: compatibility checks, migration validation harness, CI enforcement for contract changes.
- Exit gate: breaking contract/schema/topic changes fail CI unless approved via documented migration protocol.
