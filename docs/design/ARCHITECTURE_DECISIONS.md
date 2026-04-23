# Architecture Decision Records (ADR)

This file is the canonical ADR log for NITRA architecture policy decisions.

---

## ADR-0001: Runtime Technology Allocation and Control Boundaries

- Status: Accepted
- Date: 2026-04-23

### Context

The project has already seen multiple implementations of similar ingestion scope in different languages.
Without a strict runtime technology policy, NITRA risks duplicate implementations, architecture drift, and production instability.

### Decision

1. Deterministic trading core is Rust-only (mandatory):
- market ingestion connectors
- market normalization and replay controller
- bar aggregation, gap detection, backfill controller
- structure engine
- risk engine
- portfolio engine
- execution gateway and OMS state machine

2. Probabilistic/ML/AI layer is Python-only (mandatory):
- research, backtesting, dataset building
- feature engineering jobs
- online model inference services
- RAG and LLM analyst/critic services

3. Service contracts are schema-first (mandatory):
- external APIs: OpenAPI
- event streams: AsyncAPI with versioned schemas
- AI I/O: Pydantic/JSON Schema runtime validation

4. Backbone and storage policy:
- streaming backbone: Kafka/Redpanda
- hot store: TimescaleDB/Postgres
- raw immutable archive: S3/MinIO + Parquet
- vector memory: pgvector first; Qdrant only when scale requires

5. Inference and observability policy:
- inference serving: Ray Serve
- observability: OpenTelemetry + Prometheus + Grafana (Loki/Tempo when required)
- full audit trail is mandatory for decision, risk, and execution lifecycle

6. UI policy:
- operator/charting UI uses TypeScript/React (or lightweight TypeScript frontend)

7. Non-negotiable control boundary:
- LLM layer is advisory only
- only deterministic Rust execution path can place/modify/cancel orders
- if AI fails, deterministic trading continues
- if risk/execution integrity is uncertain, system fails closed

8. Anti-duplication policy:
- one runtime language per layer:
  - Rust: deterministic core
  - Python: probabilistic/AI layer
  - TypeScript: UI
- no parallel Python/Rust implementation of the same production core component

### Consequences

- Improves operational determinism and safety for production trading paths.
- Reduces engineering waste from parallel reimplementation.
- Requires explicit ADR approval for any exception.

### Enforcement

- enforced by `docs/design/nitra_system_hld.md`
- enforced by `docs/design/nitra_system_lld/01_service_catalog.md`
- deviations require new ADR referencing ADR-0001
- repository policy gates:
  - `scripts/policy/check_technology_enforcement.sh`
  - `scripts/policy/check_contract_policy.sh`
  - `make enforce-section-5-1`

### Waiver Process (Mandatory)

- Any temporary non-compliance requires an ADR-linked waiver entry with:
  - unique waiver ID
  - affected service/component
  - explicit reason
  - expiry date
- Waivers are declared in `policy/waivers.yaml`.
- Expired waivers are hard-fail policy violations.

### Migration State Model

- `compliant`: current runtime matches mandated layer runtime.
- `non_compliant_migrating`: temporary exception with active migration ticket and waiver.
- `blocked`: no net-new feature scope allowed while non-compliant; only policy-approved transitional work.

---

## ADR-0002: Development Runtime Shape (Docker-First Baseline)

- Status: Accepted
- Date: 2026-04-22

### Context

NITRA needs a stable local development runtime with low operational friction and clear service boundaries.

### Decision

Keep in Docker first:
- Kafka
- TimescaleDB
- Redis
- MinIO
- MLflow
- Prometheus
- Grafana

Keep application code mounted as source:
- structure-engine
- risk-engine
- execution-gateway
- inference-gateway
- llm-analyst

Do not add yet:
- Kubernetes
- Feast server
- Ray cluster
- separate vector DB by default
- GPU inference stack
- full HA topology
- service mesh

### Consequences

- Faster iteration and simpler debugging in early phases.
- Production topology concerns are deferred until deterministic core is stable.
