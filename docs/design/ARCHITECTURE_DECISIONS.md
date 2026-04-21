# Dev Environment Decisions

## 1. Why this shape
This environment is optimized for **Codex-led development**, which means:
- service boundaries must be explicit
- infra must be boring and predictable
- startup must be one command
- failures must be easy to isolate
- hot iteration matters more than fake completeness

## 2. What to build in Docker first
Keep in Docker:
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

## 3. What not to add yet
Do not add now:
- Kubernetes
- Feast server
- Ray cluster
- vector DB separate from Postgres
- real broker adapters
- GPU inference stack
- full HA topology
- service mesh

## 4. Why
Codex performs better when:
- file layout is stable
- service responsibilities are narrow
- compose file is not overloaded
- local commands are deterministic
- the number of failing moving parts is low
