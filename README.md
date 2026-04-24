# NITRA | AI-Native Trading Infrastructure That Stays Deterministic Under Real Market Pressure

NITRA is a Docker-first, multi-service trading platform focused on one hard promise:
**reliable market-data continuity and deterministic execution pipelines**, even when parts of the system fail or restart.

It combines real-time ingestion, canonical normalization, bar aggregation, gap detection, replay/backfill orchestration, and charting/observability into one cohesive runtime.

## Why NITRA

Most trading stacks are either fast but fragile, or robust but slow to evolve.  
NITRA is designed to deliver both:

- Deterministic core services in Rust for critical ingestion/replay paths
- Coverage-first design (rolling 90-day `1m` continuity as a first-class operational target)
- Multi-venue ingestion with normalized contracts (`oanda`, `capital`, `coinbase`)
- Recovery-oriented architecture (gap detection -> backfill -> replay)
- Built-in observability (Prometheus, Grafana, runtime health/status endpoints)
- Developer speed via Docker Compose and explicit service boundaries

## What You Get Out of the Box

- **Market ingestion pipeline** from raw venue events to canonical persisted entities
- **Time-series storage** in TimescaleDB (`raw_tick`, `ohlcv_bar`, gap/backfill lifecycle tables)
- **Backfill/replay control loop** to close missing ranges deterministically
- **Charting service** for hot/history bars, ticks, and operator backfill/coverage probes
- **Experiment and storage stack** with MLflow + MinIO + Redis + Kafka
- **Policy/test gates** for architecture/runtime contract enforcement

## Runtime Architecture (High-Level)

```text
market-ingestion-{oanda,capital,coinbase}
  -> market-normalization
  -> bar-aggregation
  -> gap-detection
  -> backfill-worker
  -> replay-controller
  -> TimescaleDB (ohlcv_bar + lifecycle tables)

charting -> reads TimescaleDB + exposes coverage/backfill APIs
prometheus/grafana -> observability
```

## Quick Start

```bash
cp .env.example .env
make up
make ps
```

Useful day-1 commands:

```bash
make logs
make charting-logs
make kafka-topics
make db
```

Open local services:

- Charting: `http://localhost:8110`
- Grafana: `http://localhost:3000`
- Prometheus: `http://localhost:9090`
- MLflow: `http://localhost:5000`

## Key Operator Endpoints

Charting service exposes practical operational APIs:

- `GET /health`
- `GET /api/v1/markets/available`
- `GET /api/v1/bars/hot`
- `GET /api/v1/bars/history`
- `GET /api/v1/ticks/hot`
- `POST /api/v1/backfill/90d`
- `POST /api/v1/backfill/window`
- `GET /api/v1/coverage/status`
- `GET /api/v1/coverage/metrics`

## Engineering Principles

- **Determinism over guesswork** in core data/recovery logic
- **Contracts over tribal knowledge** (schema/topic/API discipline)
- **Observability before optimization** (status, metrics, lifecycle tables)
- **Recovery as a feature** (gap detection and missing-only backfill)
- **Small, traceable delivery** with docs/tests updated alongside code

## Documentation Map

Start here for architecture and execution truth:

- [Project docs entrypoint](docs/README.md)
- [Global ruleset](docs/ruleset.md)
- [Ingestion domain ruleset](docs/design/ingestion/ruleset.md)
- [Execution board](docs/development/02-execution/KANBAN.md)
- [Current state memory](docs/development/04-memory/CURRENT_STATE.md)
- [Knowledgebase (RCA + playbooks)](docs/knowledgebase/README.md)

## Current Stage

NITRA is in active development with production-oriented architecture constraints.
Core ingestion and deterministic recovery loops are implemented and continuously hardened.

## Important Safety Note

This repository provides infrastructure for trading-system engineering and research.  
It is **not financial advice**, not a promise of profitability, and not a substitute for risk controls, compliance, or staged rollout practices.
