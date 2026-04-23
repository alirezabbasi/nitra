# Master Roadmap (HLD Section 5 Aligned)

Last updated: 2026-04-23

## Status legend

- `implemented`: functional baseline exists in repository
- `partial`: some parts implemented; notable gaps remain
- `scaffold`: container/interface placeholder only
- `not_started`: no implementation yet

## Module map

1. Exchange/Broker Feeds + Market Ingestion Connectors: `implemented`
2. Raw Data Lake (Object Storage archival): `partial`
3. Kafka Event Backbone: `implemented`
4. Market Normalization & Replay: `partial`
5. Deterministic Structure Engine (Rust): `scaffold`
6. Time-Series Storage (TimescaleDB): `implemented`
7. Feature Platform (Feast): `not_started`
8. Research/Backtesting/Dataset Builder + MLflow integration: `partial`
9. Online Inference Layer (Ray Serve): `not_started`
10. Risk Engine: `scaffold`
11. Portfolio Engine: `not_started`
12. RAG + LLM Analyst Layer: `scaffold`
13. Execution Gateway: `scaffold`
14. Audit/Journaling/Monitoring: `partial`

## Recommended next implementation sequence

1. Structure engine baseline (service skeleton + input/output contracts)
2. Risk engine deterministic checks baseline
3. Execution gateway order-state machine baseline
4. Replay controller consumer for `replay.commands`
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
