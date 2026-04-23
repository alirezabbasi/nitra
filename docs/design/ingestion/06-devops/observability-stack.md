# Observability Stack Runtime Contract

## Services

The compose stack includes:

- `prometheus`
- `loki`
- `tempo`
- `promtail`
- `grafana`
- `cadvisor`

## Persistent Volumes

- `prometheus_data`
- `loki_data`
- `tempo_data`
- `grafana_data`

No destructive cleanup commands are part of normal operations.

## Provisioning Paths

- Prometheus config: `infra/observability/prometheus/prometheus.yml`
- Prometheus alerts: `infra/observability/prometheus/alerts.yml`
- Loki config: `infra/observability/loki/loki-config.yml`
- Tempo config: `infra/observability/tempo/tempo.yml`
- Promtail config: `infra/observability/promtail/promtail-config.yml`
- Grafana provisioning: `infra/observability/grafana/provisioning/`
- Grafana dashboards: `infra/observability/grafana/dashboards/`

## Runbook Notes

- Start stack: `docker compose up -d`
- Check health: `make health`
- Tail observability logs:
  - `make prometheus-logs`
  - `make loki-logs`
  - `make tempo-logs`
  - `make promtail-logs`
  - `make grafana-logs`
