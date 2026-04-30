# Control-Panel Post-Cutover Observability Revalidation

- Date: 2026-04-29T21:17:39Z
- Base URL: http://localhost:8080 (container network)
- Duration seconds: 60
- Sample sleep seconds: 0.2
- Auth mode: token header enabled

## Thresholds

- HTTP success ratio (2xx/3xx): >= 99.0%
- 5xx ratio: <= 0.5%
- p95 latency per endpoint: <= 0.75s

## Results

| Endpoint | Requests | Success % | 5xx % | p95 latency (s) |
|---|---:|---:|---:|---:|
| /control-panel | 41 | 100.00 | 0.00 | 0.005 |
| /api/v1/config | 41 | 100.00 | 0.00 | 0.002 |
| /api/v1/control-panel/migration/status | 41 | 100.00 | 0.00 | 0.002 |
| /api/v1/control-panel/overview | 41 | 100.00 | 0.00 | 0.068 |
| /api/v1/charting/markets/available | 41 | 100.00 | 0.00 | 1.608 |

## Notes

- Host-shell probe to localhost:8110 failed in this environment due host-network isolation to Docker published ports.
- Container-network probe succeeded and provides live endpoint behavior evidence.
- `/api/v1/charting/markets/available` returned 200 after control-panel proxy fallback patch + container rebuild.
