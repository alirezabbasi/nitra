# 05 — Database Schema v1

## 1. Storage Split

### PostgreSQL / TimescaleDB
Use for:
- normalized market data
- bars
- structure snapshots
- feature snapshots
- orders / fills / positions
- audit and ops metadata

### Object Storage
Use for:
- raw market event archive
- replay files
- model artifacts
- batch research artifacts

### pgvector
Use for:
- framework docs
- scenario embeddings
- journal embeddings
- postmortem retrieval

---

## 2. Core Tables

## 2.1 Market Data

### `ticks`
```sql
CREATE TABLE ticks (
  id BIGSERIAL PRIMARY KEY,
  venue TEXT NOT NULL,
  symbol TEXT NOT NULL,
  ts TIMESTAMPTZ NOT NULL,
  price DOUBLE PRECISION NOT NULL,
  size DOUBLE PRECISION NOT NULL,
  side TEXT NULL,
  source_seq TEXT NULL,
  ingest_ts TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### `bars_1m`
```sql
CREATE TABLE bars_1m (
  id BIGSERIAL PRIMARY KEY,
  venue TEXT NOT NULL,
  symbol TEXT NOT NULL,
  bucket_start TIMESTAMPTZ NOT NULL,
  bucket_end TIMESTAMPTZ NOT NULL,
  open DOUBLE PRECISION NOT NULL,
  high DOUBLE PRECISION NOT NULL,
  low DOUBLE PRECISION NOT NULL,
  close DOUBLE PRECISION NOT NULL,
  volume DOUBLE PRECISION NOT NULL,
  finalized BOOLEAN NOT NULL DEFAULT true,
  UNIQUE (venue, symbol, bucket_start)
);
```

> Repeat as hypertables for each required timeframe or use one partitioned bars table with timeframe column.

---

## 2.2 Structure Tables

### `structure_snapshots`
```sql
CREATE TABLE structure_snapshots (
  id UUID PRIMARY KEY,
  venue TEXT NOT NULL,
  symbol TEXT NOT NULL,
  timeframe TEXT NOT NULL,
  snapshot_ts TIMESTAMPTZ NOT NULL,
  directional_bias TEXT NOT NULL,
  liquidity_side TEXT NOT NULL,
  liquidity_target DOUBLE PRECISION NULL,
  reference_candle_id TEXT NULL,
  reference_high DOUBLE PRECISION NULL,
  reference_low DOUBLE PRECISION NULL,
  pullback_state TEXT NOT NULL,
  archive_version BIGINT NOT NULL,
  major_active BOOLEAN NOT NULL DEFAULT false,
  payload JSONB NOT NULL
);
```

### `minor_structures`
```sql
CREATE TABLE minor_structures (
  id UUID PRIMARY KEY,
  structure_snapshot_id UUID NOT NULL REFERENCES structure_snapshots(id),
  venue TEXT NOT NULL,
  symbol TEXT NOT NULL,
  timeframe TEXT NOT NULL,
  minor_low DOUBLE PRECISION NOT NULL,
  minor_high DOUBLE PRECISION NOT NULL,
  confirmed_at TIMESTAMPTZ NOT NULL
);
```

### `major_structures`
```sql
CREATE TABLE major_structures (
  id UUID PRIMARY KEY,
  structure_snapshot_id UUID NOT NULL REFERENCES structure_snapshots(id),
  venue TEXT NOT NULL,
  symbol TEXT NOT NULL,
  timeframe TEXT NOT NULL,
  major_low DOUBLE PRECISION NOT NULL,
  major_high DOUBLE PRECISION NOT NULL,
  trigger_structure_id UUID NULL,
  confirmed_at TIMESTAMPTZ NOT NULL
);
```

---

## 2.3 Feature Tables

### `feature_definitions`
```sql
CREATE TABLE feature_definitions (
  id UUID PRIMARY KEY,
  feature_name TEXT NOT NULL,
  feature_version TEXT NOT NULL,
  owner_team TEXT NOT NULL,
  logic_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (feature_name, feature_version)
);
```

### `feature_snapshots`
```sql
CREATE TABLE feature_snapshots (
  id UUID PRIMARY KEY,
  venue TEXT NOT NULL,
  symbol TEXT NOT NULL,
  timeframe TEXT NOT NULL,
  as_of TIMESTAMPTZ NOT NULL,
  feature_set_version TEXT NOT NULL,
  features JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## 2.4 Model Tables

### `model_registry_cache`
```sql
CREATE TABLE model_registry_cache (
  id UUID PRIMARY KEY,
  model_name TEXT NOT NULL,
  model_version TEXT NOT NULL,
  stage TEXT NOT NULL,
  signature JSONB NOT NULL,
  metadata JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (model_name, model_version)
);
```

---

## 2.5 Decision Tables

### `signal_scores`
```sql
CREATE TABLE signal_scores (
  id UUID PRIMARY KEY,
  structure_snapshot_id UUID NOT NULL REFERENCES structure_snapshots(id),
  feature_snapshot_id UUID NOT NULL REFERENCES feature_snapshots(id),
  model_name TEXT NOT NULL,
  model_version TEXT NOT NULL,
  score DOUBLE PRECISION NOT NULL,
  confidence DOUBLE PRECISION NOT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### `risk_decisions`
```sql
CREATE TABLE risk_decisions (
  id UUID PRIMARY KEY,
  signal_score_id UUID NOT NULL REFERENCES signal_scores(id),
  account_id TEXT NOT NULL,
  strategy_id TEXT NOT NULL,
  approved BOOLEAN NOT NULL,
  rejection_reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
  max_allowed_qty DOUBLE PRECISION NULL,
  risk_snapshot JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### `trade_decisions`
```sql
CREATE TABLE trade_decisions (
  id UUID PRIMARY KEY,
  structure_snapshot_id UUID NOT NULL REFERENCES structure_snapshots(id),
  feature_snapshot_id UUID NOT NULL REFERENCES feature_snapshots(id),
  signal_score_id UUID NOT NULL REFERENCES signal_scores(id),
  risk_decision_id UUID NOT NULL REFERENCES risk_decisions(id),
  llm_analysis_id UUID NULL,
  final_decision TEXT NOT NULL,
  rationale JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## 2.6 Execution Tables

### `orders`
```sql
CREATE TABLE orders (
  id UUID PRIMARY KEY,
  account_id TEXT NOT NULL,
  strategy_id TEXT NOT NULL,
  venue TEXT NOT NULL,
  symbol TEXT NOT NULL,
  side TEXT NOT NULL,
  order_type TEXT NOT NULL,
  tif TEXT NOT NULL,
  qty DOUBLE PRECISION NOT NULL,
  limit_price DOUBLE PRECISION NULL,
  stop_price DOUBLE PRECISION NULL,
  status TEXT NOT NULL,
  broker_order_id TEXT NULL,
  submitted_at TIMESTAMPTZ NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### `order_events`
```sql
CREATE TABLE order_events (
  id BIGSERIAL PRIMARY KEY,
  order_id UUID NOT NULL REFERENCES orders(id),
  event_type TEXT NOT NULL,
  event_ts TIMESTAMPTZ NOT NULL,
  payload JSONB NOT NULL
);
```

### `fills`
```sql
CREATE TABLE fills (
  id UUID PRIMARY KEY,
  order_id UUID NOT NULL REFERENCES orders(id),
  venue TEXT NOT NULL,
  symbol TEXT NOT NULL,
  fill_ts TIMESTAMPTZ NOT NULL,
  fill_qty DOUBLE PRECISION NOT NULL,
  fill_price DOUBLE PRECISION NOT NULL,
  liquidity_flag TEXT NULL,
  fee DOUBLE PRECISION NULL,
  payload JSONB NOT NULL
);
```

### `positions`
```sql
CREATE TABLE positions (
  id UUID PRIMARY KEY,
  account_id TEXT NOT NULL,
  strategy_id TEXT NOT NULL,
  venue TEXT NOT NULL,
  symbol TEXT NOT NULL,
  net_qty DOUBLE PRECISION NOT NULL,
  avg_price DOUBLE PRECISION NOT NULL,
  realized_pnl DOUBLE PRECISION NOT NULL DEFAULT 0,
  unrealized_pnl DOUBLE PRECISION NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (account_id, strategy_id, venue, symbol)
);
```

---

## 2.7 AI / Retrieval Tables

### `analysis_records`
```sql
CREATE TABLE analysis_records (
  id UUID PRIMARY KEY,
  structure_snapshot_id UUID NOT NULL REFERENCES structure_snapshots(id),
  retrieval_refs JSONB NOT NULL,
  framework_alignment TEXT NOT NULL,
  confidence DOUBLE PRECISION NOT NULL,
  analysis JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### `knowledge_chunks`
```sql
CREATE TABLE knowledge_chunks (
  id UUID PRIMARY KEY,
  doc_type TEXT NOT NULL,
  doc_ref TEXT NOT NULL,
  chunk_text TEXT NOT NULL,
  metadata JSONB NOT NULL,
  embedding vector(1536)
);
```

---

## 2.8 Audit Tables

### `audit_events`
```sql
CREATE TABLE audit_events (
  id BIGSERIAL PRIMARY KEY,
  trace_id TEXT NOT NULL,
  actor_type TEXT NOT NULL,
  actor_id TEXT NULL,
  action TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## 3. Indexing Guidance
- index `(venue, symbol, ts)` on ticks
- unique `(venue, symbol, bucket_start)` on bars
- index `(venue, symbol, timeframe, snapshot_ts DESC)` on structure snapshots
- index `(account_id, strategy_id, venue, symbol)` on positions
- GIN on JSONB policy and rationale fields where queried
- vector index on `knowledge_chunks.embedding`

## 4. Timescale Guidance
- create hypertables on market time columns
- use continuous aggregates for higher-level bar/query workloads
- compression and retention policies should be applied by environment and query profile
