# AI Trading Dev Environment Scaffold

This scaffold is a **development-first** Docker setup for the AI-enabled trading platform.

## Goal
Start with the minimum platform that lets you:
- ingest and replay market events
- persist time-series data
- run deterministic structure logic
- run risk and execution path locally
- track experiments in MLflow
- keep observability wired in
- let Codex generate code against stable service boundaries

## What is intentionally included
- PostgreSQL + TimescaleDB
- Kafka in KRaft mode
- Redis
- MinIO (S3-compatible local object store)
- MLflow
- Prometheus + Grafana
- Charting UI (Kline/Candlestick)
- lightweight service containers / placeholders

## What is intentionally excluded for now
- Feast server in dev
- Ray cluster in dev
- GPU LLM serving in dev
- Kubernetes in dev
- full HA topology

Those come later. This scaffold is for **fast local iteration**.

## Start
```bash
cp .env.example .env
make up
make ps
```

## Initial service build order
1. structure-engine
2. risk-engine
3. execution-gateway
4. market-ingestion
5. inference-gateway
6. llm-analyst
