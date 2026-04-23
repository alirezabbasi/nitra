# Repository Layout (EPIC-01)

EPIC-01 establishes a Rust-first monorepo layout.

## Top-Level

- `crates/`: shared libraries (domain models, contracts).
- `services/`: executable service crates.
- `.github/workflows/`: CI workflows.
- `docs/`: architecture and delivery documentation.

## Shared Crates

- `crates/domain`: canonical market/trading domain types.
- `crates/contracts`: message envelope and stream contract types.

## Service Crates (Skeletons)

- `services/connector`
- `services/normalizer`
- `services/bar_engine`
- `services/gap_engine`
- `services/backfill_worker`
- `services/archive_worker`
- `services/risk_gateway`
- `services/oms`
- `services/query_api`

Each service currently boots logging and reports readiness at startup; behavior implementation continues in later epics.
