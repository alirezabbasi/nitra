# Observability and SLO Enforcement

## EPIC-10 Objective

Establish end-to-end operational visibility with metrics, logs, traces plumbing, dashboards, and actionable alert rules.

## Stack Components

- Metrics: Prometheus (`prometheus`)
- Logs: Loki (`loki`) + Promtail (`promtail`)
- Traces backend: Tempo (`tempo`)
- Dashboards: Grafana (`grafana`)
- Container resource telemetry: cAdvisor (`cadvisor`)

## Service Instrumentation (Current)

`risk_gateway` and `oms` expose:

- `/health`
- `/ready`
- `/metrics` (Prometheus exposition format)

Key counters:

- `risk_gateway_orders_processed_total`
- `risk_gateway_orders_allowed_total`
- `risk_gateway_orders_rejected_total`
- `oms_orders_submitted_total`
- `oms_orders_rejected_total`
- `oms_reconcile_hold_total`

## Alert Policy Families

Prometheus rules in `infra/observability/prometheus/alerts.yml`:

1. Availability:
- `RiskGatewayDown`
- `OmsDown`

2. SLO signal anomalies:
- `RiskRejectRateSpike`
- `OmsReconcileHoldGrowth`

## Dashboards

Provisioned Grafana dashboards:

- `BarsFP Overview`
- `BarsFP SLO Signals`

These are auto-loaded from `infra/observability/grafana/dashboards/`.

## Drill Expectation

Use the dashboard + alert set to complete detection -> diagnosis -> recovery drills with evidence captured in EPIC logs.

## DEV-00074 Enforcement Checks

- Kafka topic policy updates are guarded by validation checks on:
  - allowed topic names (must exist in `infra/kafka/topics.csv`),
  - partition bounds,
  - retention bounds,
  - lag SLO bounds,
  - cleanup policy bounds,
  - ISR bounds.
- Control-panel endpoint:
  - `POST /api/v1/control-panel/ingestion/kafka-topic-policy`
- Ingestion payload visibility includes:
  - `kafka_topic_policies`
  - `kafka_runtime`
  - `metrics.kafka_topics_tracked`
