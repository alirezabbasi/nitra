# DEV-00002 Reuse Map: BarsFP -> NITRA Ingestion

## Decision Rules

- `reuse-as-is`: copy with only path/namespace renaming, no logic change.
- `adapt`: keep core logic but modify contracts/naming/runtime integration for NITRA.
- `reject`: do not import.

## Reuse Mapping

| BarsFP Source | NITRA Target | Decision | Notes |
|---|---|---|---|
| `../barsfp/crates/contracts/src/lib.rs` | `services/ingestion/contracts` (new) | adapt | Keep envelope, retry metadata, order/risk message patterns; rename `barsfp_*` and trim unused contract types. |
| `../barsfp/crates/domain/src/lib.rs` | `services/ingestion/domain` (new) | adapt | Keep canonical event + bar structs; align to NITRA naming/schema versioning. |
| `../barsfp/services/connector/src/main.rs` | `services/market-ingestion/src/main.rs` | adapt | Keep multi-venue adapter runtime patterns; align env vars/topics/logging to NITRA. |
| `../barsfp/services/normalizer/src/main.rs` | `services/market-normalization/src/main.rs` | adapt | Keep canonical transformation + classification + persistence guards; rewire to NITRA topics and schema. |
| `../barsfp/services/bar_engine/src/main.rs` | `services/bar-aggregation/src/main.rs` | adapt | Keep deterministic minute aggregation + explicit commit flow; align table/topic names. |
| `../barsfp/services/gap_engine/src/main.rs` | `services/gap-detection/src/main.rs` | adapt | Keep gap state logic and dedupe behavior; trim non-required features for initial NITRA scope. |
| `../barsfp/services/backfill_worker/src/main.rs` | `services/backfill-worker/src/main.rs` | adapt | Keep missing-only backfill/replay flow; adapt from Redpanda defaults to Kafka defaults. |
| `../barsfp/infra/timescaledb/init/001_init_hot_store.sql` | `infra/timescaledb/init/` (new in NITRA) | adapt | Keep `ohlcv_bar` baseline; remove compatibility legacy views unless needed. |
| `../barsfp/infra/timescaledb/init/007_processed_message_ledger.sql` | `infra/timescaledb/init/` | reuse-as-is | Core dedupe ledger fits NITRA directly. |
| `../barsfp/infra/timescaledb/init/008_market_event_entities.sql` | `infra/timescaledb/init/` | adapt | Keep `raw_tick/trade_print/book_event`; align DB names/index conventions. |
| `../barsfp/infra/symbols/registry.v1.json` | `infra/symbols/registry.v1.json` | adapt | Keep structure; seed with NITRA-approved instruments only. |
| `../barsfp/tests/epic-12/*` | `tests/ingestion/replay-idempotency/*` | adapt | Keep replay/idempotency intent; rewrite to NITRA service names/paths. |
| `../barsfp/tests/epic-21/*` | `tests/ingestion/canonical-persistence/*` | adapt | Keep schema/entity verification intent; rewrite path/topic expectations. |

## Strict Reject List (Do Not Import)

- `../barsfp/ruleset.md` and BarsFP governance/process docs.
- `../barsfp/docs/` content except selective technical reference while rewriting NITRA docs.
- `../barsfp/infra/observability/loki/*`
- `../barsfp/infra/observability/tempo/*`
- `../barsfp/infra/observability/promtail/*`
- `../barsfp/services/chart_ui/*`
- `../barsfp/services/cold_loader/*` (deferred)
- `../barsfp/services/archive_worker/*` (deferred)
- `../barsfp/services/query_api/*` (deferred)
- `../barsfp/infra/clickhouse/*` (deferred)
- Any Redpanda-only bootstrap/runtime tooling that is not portable to NITRA Kafka flow.

## Minimal Migration Plan

1. Land contracts/domain subset and symbol registry shape (`adapt` only what current ingestion path requires).
2. Land schema baseline (`ohlcv_bar`, market entities, processed ledger).
3. Wire connector + normalizer + bar engine in NITRA compose.
4. Add gap/backfill minimal path.
5. Add replay/idempotency tests and close with dev runbook.

## HLD Alignment

- Supports event-driven market data platform and deterministic ingestion core.
- Preserves replay-safe and auditable processing.
- Avoids importing non-essential operational complexity into baseline dev environment.
