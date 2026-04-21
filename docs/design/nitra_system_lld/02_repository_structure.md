# 02 — Repository Structure

## Option A — Monorepo (recommended initially)

```text
trading-platform/
├── services/
│   ├── market-ingestion/           # Rust
│   ├── market-normalization/       # Rust
│   ├── bar-aggregation/            # Rust
│   ├── structure-engine/           # Rust
│   ├── feature-gateway/            # Python
│   ├── research-orchestrator/      # Python
│   ├── model-training/             # Python
│   ├── inference-gateway/          # Python
│   ├── risk-engine/                # Rust
│   ├── portfolio-engine/           # Rust
│   ├── execution-gateway/          # Rust
│   ├── rag-indexer/                # Python
│   ├── llm-analyst/                # Python
│   └── observability-api/          # Go or Python
├── libs/
│   ├── rust/
│   │   ├── event-models/
│   │   ├── structure-core/
│   │   ├── risk-policies/
│   │   ├── order-state-machine/
│   │   └── shared-utils/
│   ├── python/
│   │   ├── feature-contracts/
│   │   ├── model-contracts/
│   │   ├── prompt-contracts/
│   │   └── eval-utils/
│   └── schemas/
│       ├── avro/
│       ├── jsonschema/
│       ├── openapi/
│       └── asyncapi/
├── infra/
│   ├── k8s/
│   │   ├── base/
│   │   ├── overlays/dev/
│   │   ├── overlays/staging/
│   │   └── overlays/prod/
│   ├── terraform/
│   ├── helm/
│   └── observability/
├── data/
│   ├── replay-scenarios/
│   ├── sample-fixtures/
│   └── eval-benchmarks/
├── docs/
│   ├── hld/
│   ├── lld/
│   ├── adr/
│   ├── runbooks/
│   └── threat-model/
├── scripts/
├── Makefile
└── README.md
```

## Branching Model
- `main` → protected, releasable
- `develop` → integration
- `feature/*`
- `fix/*`
- `release/*`

## Repo Governance
- mandatory PR review
- CI required
- schema compatibility checks
- contract tests for APIs and Kafka events
- migration review required for DB changes

## ADRs Required For
- new external dependency
- DB partition strategy change
- order state transition change
- risk rule change
- model promotion criteria change
