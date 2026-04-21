# Runtime Topology (LLD)

## Core Runtime Pipeline

1. Broker adapters publish raw market events (`raw.market.<venue>`).
2. Normalizer converts raw events into canonical events (`normalized.quote.fx` and future normalized topics).
3. Bar engine builds deterministic bars (`bar.1m`).
4. Gap engine detects coverage holes (`gap.events`).
5. Backfill worker issues replay commands and audit records.
6. Archive worker writes immutable lakehouse files.
7. Cold loader imports archive data into ClickHouse.
8. Query API serves hot/cold query paths.
9. Risk gateway + OMS handle deterministic execution lifecycle.

## Design Boundaries

- Adapters are ingestion-only and venue-specific.
- Normalizer is schema enforcement boundary.
- Execution path remains deterministic (LLM cannot place orders).
- All inter-service exchange is event-driven with explicit topics.
