# Master Roadmap (HLD Section 5 Aligned)

Last updated: 2026-04-24

## Status legend

- `implemented`: functional baseline exists in repository
- `partial`: some parts implemented; notable gaps remain
- `scaffold`: container/interface placeholder only
- `not_started`: no implementation yet
- Technology compliance:
  - `compliant`: matches Section 5.1 runtime mandate
  - `non_compliant_migrating`: temporary waiver + migration ticket
  - `blocked`: not active for net-new non-compliant scope

## Module map

| # | Module | Implementation Status | Technology Compliance |
|---|---|---|---|
| 1 | Exchange/Broker Feeds + Market Ingestion Connectors | `implemented` | `compliant` |
| 2 | Raw Data Lake (Object Storage archival) | `partial` | `compliant` |
| 3 | Kafka Event Backbone | `implemented` | `compliant` |
| 4 | Market Normalization & Replay | `partial` | `compliant` |
| 5 | Deterministic Structure Engine (Rust) | `scaffold` | `compliant` |
| 6 | Time-Series Storage (TimescaleDB) | `implemented` | `compliant` |
| 7 | Feature Platform (Feast) | `not_started` | `blocked` |
| 8 | Research/Backtesting/Dataset Builder + MLflow integration | `partial` | `compliant` |
| 9 | Online Inference Layer (Ray Serve) | `not_started` | `compliant` |
| 10 | Risk Engine | `scaffold` | `compliant` |
| 11 | Portfolio Engine | `not_started` | `blocked` |
| 12 | RAG + LLM Analyst Layer | `scaffold` | `compliant` |
| 13 | Execution Gateway | `scaffold` | `compliant` |
| 14 | Audit/Journaling/Monitoring | `partial` | `compliant` |
| 15 | Bar Aggregation + Gap Detection + Backfill Controller | `implemented` | `compliant` |

## Recommended next implementation sequence

1. `DEV-00013`: startup 90-day `1m` coverage enforcement and missing-only backfill for all active instruments
2. Structure engine baseline (service skeleton + input/output contracts)
3. Risk engine deterministic checks baseline
4. Execution gateway order-state machine baseline
5. Audit/journal events for deterministic decision path
6. Feature platform bootstrap (contract-first)
7. Inference gateway service logic with schema validation
8. RAG/LLM advisory path with strict boundaries

## Gate policy between modules

No module should move to `implemented` unless:

- runtime behavior exists
- minimum test coverage exists
- docs are updated in `docs/design` and/or domain docs
- memory system reflects the new state
- Section 5.1 policy gate passes (`make enforce-section-5-1`)
