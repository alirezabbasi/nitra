# Control Panel Service Migration Map (DEV-00045 Freeze)

## Purpose

Freeze the migration contract from the current monolithic implementation (`services/charting`) to the target modular `control-panel-service` structure.

## Source of Truth

- Current runtime: `services/charting/app.py`, `services/charting/static/control-panel.html`
- Target architecture: `docs/design/ingestion/07-devdocs/04-lld-services/control-panel-service.md`

## Backend Migration Map (`app.py` -> target modules)

| Current Concern in `services/charting/app.py` | Target Module Path | Delivery Ticket |
| --- | --- | --- |
| FastAPI bootstrap, middleware, route registration | `services/control-panel/app/main.py` | `DEV-00046` |
| Auth/session helpers and RBAC checks | `services/control-panel/app/core/security.py` + `app/api/routers/session.py` | `DEV-00046`, `DEV-00047` |
| Control-panel overview and module APIs | `services/control-panel/app/api/routers/overview.py` + `app/services/control_panel/overview_service.py` | `DEV-00047` |
| Ingestion operations handlers | `services/control-panel/app/api/routers/ingestion.py` + `app/services/control_panel/ingestion_service.py` | `DEV-00047` |
| Risk/portfolio handlers | `services/control-panel/app/api/routers/risk_portfolio.py` + `app/services/control_panel/risk_portfolio_service.py` | `DEV-00047` |
| Execution handlers | `services/control-panel/app/api/routers/execution.py` + `app/services/control_panel/execution_service.py` | `DEV-00047` |
| Ops/runbook/research/config handlers | Domain routers under `app/api/routers/` + matching `app/services/control_panel/*` | `DEV-00047` |
| Charting endpoints (`bars/ticks/markets/backfill/coverage`) | `services/control-panel/app/api/routers/charting.py` + `app/services/charting/*` | `DEV-00048` |
| Direct SQL blocks | `services/control-panel/app/db/repositories/*.py` | `DEV-00047`, `DEV-00048` |
| Venue adapter requests/retry helpers | `services/control-panel/app/integrations/venue_clients/*.py` | `DEV-00048` |

## Frontend Migration Map (`control-panel.html` -> target modules)

| Current Concern in `services/charting/static/control-panel.html` | Target Module Path | Delivery Ticket |
| --- | --- | --- |
| Full-page shell layout and sidebar | `services/control-panel/frontend/src/app/shell/*` | `DEV-00049` |
| Inline route/module switching | `services/control-panel/frontend/src/app/routes/*` | `DEV-00049` |
| Domain-specific rendering blocks | `services/control-panel/frontend/src/modules/*` | `DEV-00049` |
| Shared UI patterns/tables/forms | `services/control-panel/frontend/src/components/*` | `DEV-00049` |
| Inline fetch/network logic | `services/control-panel/frontend/src/services/api-client/*` | `DEV-00049` |
| Session token and role state logic | `services/control-panel/frontend/src/state/session/*` | `DEV-00049` |
| Preferences and density/layout persistence | `services/control-panel/frontend/src/state/preferences/*` | `DEV-00049` |
| Inline CSS theme/tokens | `services/control-panel/frontend/src/styles/tokens.css`, `theme.css` | `DEV-00049` |

## API Compatibility Matrix (Current -> Target)

| Current Route Pattern | Target Owner | Compatibility Mode |
| --- | --- | --- |
| `/control-panel` | control-panel shell router | retained, no path change |
| `/api/v1/control-panel/*` | domain routers in `app/api/routers/` | retained, no path change |
| `/api/v1/bars/*` | charting router module | retained path, shim during extraction |
| `/api/v1/ticks/*` | charting router module | retained path, shim during extraction |
| `/api/v1/markets/*` | charting router module | retained path, shim during extraction |
| `/api/v1/venues/*` | charting router module | retained path, shim during extraction |
| `/api/v1/backfill/*` | charting + ingestion shared modules | retained path, shim during extraction |
| `/api/v1/coverage/*` | charting + ingestion shared modules | retained path, shim during extraction |

Compatibility headers for shim routes are mandatory:

- `X-Nitra-Compat: legacy`
- `Deprecation: true`
- `Sunset: <RFC3339>`
- `Link: <deprecation runbook>`

## Rollout and Fallback Contract

1. Keep legacy code path available while each target module reaches parity.
2. Validate route parity with contract tests before switching default handlers.
3. Switch one domain at a time and monitor error/latency deltas.
4. On critical regression, revert domain handler to prior compatibility path.
5. Retire shims only after `DEV-00051` acceptance gate and documented sunset completion.
