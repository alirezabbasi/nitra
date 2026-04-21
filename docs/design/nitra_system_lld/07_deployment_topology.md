# 07 — Deployment Topology

## 1. Environment Topology

### Dev
- single-node Kafka acceptable
- single Postgres/Timescale instance
- mock broker
- local object storage
- CPU-only inference acceptable

### Staging / Paper
- real market feeds
- simulated execution
- HA Kafka preferred
- prod-like observability
- replay sidecar enabled

### Production
- isolated Kubernetes namespace / cluster segment
- HA Kafka
- HA PostgreSQL/Timescale
- durable object storage
- separated CPU and GPU node pools
- external secret management
- dedicated ingress controls
- alerting integrated with incident tooling

---

## 2. Kubernetes Workload Map

### Deployments
- feature-gateway
- inference-gateway
- llm-analyst
- rag-indexer workers
- observability-api
- API ingress layer

### StatefulSets
- Kafka brokers
- PostgreSQL/Timescale
- ZooKeeper/KRaft components depending on deployment mode
- optional dedicated vector service if later separated

### Jobs / CronJobs
- feature backfills
- replay jobs
- nightly data-quality checks
- model evaluation suite
- embedding reindex jobs
- retention/compression verification jobs

---

## 3. Node Pool Strategy

### CPU General Pool
- ingestion
- normalization
- bars
- structure
- risk
- portfolio
- execution

### CPU Batch Pool
- replays
- backfills
- training prep
- eval jobs

### GPU Pool
- LLM inference
- heavy deep-learning inference
- selective training jobs if not off-cluster

---

## 4. Networking Model
- ingress gateway for public/internal APIs
- private service mesh or internal mTLS between services
- broker/exchange egress restricted by policy
- DB access only from approved namespaces/services
- audit sink isolated from application writers

---

## 5. Secrets and Config
- secrets from external manager
- no broker/API keys in ConfigMaps
- environment overlays per stage
- feature flags for strategy enablement and kill switches

---

## 6. Failure Isolation
- LLM services isolated so failures do not block deterministic trading path
- training and research workloads isolated from live services
- execution gateway isolated with stricter PodDisruptionBudget and priority class
- risk engine isolated and deployed redundantly

---

## 7. Disaster Recovery
- object storage is replay source of truth for raw events
- PostgreSQL backups with tested restore
- Kafka topic replication configured per environment
- documented broker reconciliation procedure
- infrastructure recreated from IaC only

---

## 8. Recommended Runtime Sequence
1. start infra
2. start ingestion
3. validate feed health
4. start normalization and bars
5. start structure engine
6. start feature and portfolio services
7. start inference
8. start risk
9. start execution in dry-run
10. lift to paper/live mode with explicit operator action
