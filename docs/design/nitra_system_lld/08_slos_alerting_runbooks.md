# 08 — SLOs, Alerting, and Runbooks

## 1. Core SLOs

### Market Data
- raw feed freshness lag < 2s for real-time venues
- normalized event validation success > 99.95%
- bar finalization delay < 1 bucket + 1s

### Structure Engine
- structure snapshot generation latency p95 < 50ms after bar close
- state persistence success > 99.99%

### Feature / Inference
- online feature fetch p95 < 20ms
- inference p95 < 30ms
- end-to-end score generation p95 < 75ms

### Risk / Execution
- pre-trade risk p95 < 10ms
- intent-to-submit p95 < 50ms internal overhead
- broker reconciliation mismatch rate < 0.1%

### AI Layer
- schema-valid analysis rate > 99%
- contradiction rate with deterministic state < 0.5%
- retrieval latency p95 < 150ms

---

## 2. Alert Classes

### P1
- risk engine unavailable
- execution reconciliation failure
- broker rejects spike above threshold
- stale market data beyond hard threshold
- kill switch unexpectedly disabled/enabled

### P2
- feature freshness breach
- inference latency breach
- Kafka consumer lag on live topics
- PostgreSQL replication lag
- LLM schema failure rate spike

### P3
- dashboard degradation
- non-critical batch job failures
- embedding pipeline lag

---

## 3. Golden Signals
- feed freshness
- Kafka consumer lag
- bar generation lag
- structure snapshot lag
- feature freshness
- inference latency
- risk approval rate
- reject rate
- order ack latency
- fill latency
- slippage drift
- reconciliation mismatches

---

## 4. Runbooks

### Feed Stale
1. confirm venue outage vs internal outage
2. inspect ingress and Kafka producer health
3. compare raw topic write rate to expected baseline
4. if stale beyond threshold, halt strategies for affected venue
5. backfill gaps after recovery

### Reconciliation Error
1. freeze affected strategy/venue
2. pull broker open orders and positions
3. compare to internal order/position state
4. resolve manually if needed
5. replay order events into audit report
6. do not resume until reconciled

### Risk Engine Unavailable
1. trading must fail closed automatically
2. verify replicas and dependencies
3. inspect dependency health: portfolio, balances, policy store
4. restore service
5. run synthetic pre-trade test before enabling

### LLM Layer Contradiction Spike
1. keep trading path deterministic
2. disable LLM advisory in production if threshold exceeded
3. inspect retrieval context drift
4. inspect prompt or schema release changes
5. rerun benchmark suite before re-enabling
