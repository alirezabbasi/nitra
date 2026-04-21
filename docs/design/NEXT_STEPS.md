# Suggested Build Order

## Phase 1 — deterministic spine
1. structure-engine crate
2. DB migrations
3. Kafka topic bootstrap script
4. risk-engine skeleton
5. execution-gateway order state machine skeleton

## Phase 2 — event path
1. market-ingestion service
2. market-normalization service
3. bar aggregation service
4. structure snapshot emission
5. audit trail writes

## Phase 3 — model path
1. inference-gateway API
2. MLflow integration
3. feature snapshot tables
4. offline training scripts
5. schema-validated score responses

## Phase 4 — AI path
1. knowledge chunk schema
2. retrieval pipeline
3. llm-analyst output contract
4. contradiction checker against structure state
