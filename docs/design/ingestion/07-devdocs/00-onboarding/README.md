# Onboarding Guide

## Day 0: Prerequisites

- Git
- Docker Engine + Docker Compose plugin
- Rust toolchain (version from `rust-toolchain.toml`)
- Make

## Day 1: Repository Orientation

1. Read `ruleset.md`.
2. Read `docs/design/nitra_system_hld.md` and `docs/design/AI-enabled_trading_decision_platform.md` (HLD baseline).
3. Read `docs/README.md` for project doc map.
4. Read `docs/design/ingestion/07-devdocs/` in order.
5. Read `python-fastapi-to-rust-orientation.md` for stack translation.

## Day 1: Run Project Locally

1. Copy `.env.example` to `.env`.
2. Start stack: `docker compose up -d`.
3. Verify services: `docker compose ps`.
4. Check core logs:
   - `docker compose logs -f --tail=200 market-ingestion market-ingestion-capital market-ingestion-coinbase market-normalization`

## Ownership Model

Every developer must be able to:

- implement one service end-to-end,
- add/update tests in `tests/epic-*`,
- update docs with every meaningful change,
- provide safe Docker-first runtime behavior.
