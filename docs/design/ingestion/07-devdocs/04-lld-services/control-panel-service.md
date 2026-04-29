# Control Panel Service (`control-panel-service`)

## Purpose

`control-panel-service` is the operator-facing web and API surface for NITRA control-plane workflows. It unifies admin modules (overview, ingestion, risk, portfolio, execution, ops, research, config) while embedding charting as a first-class module.

## Architectural Position

- Replaces charting-first service framing with control-panel-first framing.
- Hosts both:
  - control-panel APIs and UI shell,
  - charting APIs and chart workbench integration.
- Maintains compatibility with existing charting routes during migration window.

## Backend Target Structure

```text
services/control-panel/
  app/
    main.py
    api/
      routers/
        overview.py
        session.py
        ingestion.py
        risk_portfolio.py
        execution.py
        ops.py
        research.py
        config.py
        search.py
        charting.py
    core/
      config.py
      security.py
      logging.py
      errors.py
    db/
      session.py
      repositories/
    services/
      control_panel/
      charting/
    integrations/
      venue_clients/
    models/
      requests.py
      responses.py
```

### Backend Module Ownership (Frozen)

- `app/main.py`: FastAPI bootstrap, router composition, startup/shutdown hooks.
- `app/api/routers/*.py`: transport-only handlers (request parsing, response serialization, route-level auth checks).
- `app/services/control_panel/*.py`: control-panel business orchestration by domain.
- `app/services/charting/*.py`: charting business orchestration and bridge logic.
- `app/db/repositories/*.py`: SQL access and persistence contracts only.
- `app/integrations/venue_clients/*.py`: external venue/backfill adapter clients.
- `app/core/*.py`: config, security, logging, error model, and observability primitives.
- `app/models/*.py`: typed request/response/domain DTO contracts.

## Frontend Target Structure

```text
services/control-panel/frontend/
  src/
    app/
      shell/
      routes/
    modules/
      overview/
      ingestion/
      risk-portfolio/
      execution/
      charting/
      ops/
      research/
      config/
    components/
      layout/
      tables/
      forms/
      feedback/
    services/
      api-client/
      auth/
      search/
    state/
      session/
      preferences/
    styles/
      tokens.css
      theme.css
```

### Frontend Module Ownership (Frozen)

- `src/app/shell`: app frame, sidebar, command palette container, global shortcuts.
- `src/app/routes`: route wiring and module boundaries.
- `src/modules/*`: domain-specific screens/workflows.
- `src/components/*`: shared, style-system-compliant UI primitives.
- `src/services/*`: API client, auth/session, query transport/error handling.
- `src/state/*`: session state, preferences state, cross-module stores.
- `src/styles/*`: design tokens/theme and global utility styles.

## Migration Contract

- Keep current endpoint behavior while internals are split.
- Preserve control-panel route entrypoint (`/control-panel`).
- Preserve chart surface routes used by operator workflows.
- Use compatibility headers and explicit deprecation schedule for any path relocation.

### Compatibility Header Contract (Frozen)

- Header name: `X-Nitra-Compat`
- Required values:
  - `legacy` for compatibility shim route handling.
  - `native` for post-cutover module-native handling.
- Deprecation metadata headers on shimmed responses:
  - `Deprecation: true`
  - `Sunset: <RFC3339 timestamp>`
  - `Link: <runbook/deprecation doc>`

### API and UI Compatibility Guarantees (Frozen)

- Preserve behavior for existing high-value routes through migration:
  - `/control-panel`
  - `/api/v1/control-panel/*`
  - `/api/v1/bars/*`, `/api/v1/ticks/*`, `/api/v1/markets/*`, `/api/v1/venues/*`
  - `/api/v1/backfill/*`, `/api/v1/coverage/*`
- Preserve control-panel charting handoff behavior (`Full Chart` and `openChartWorkbench` pathways).
- Preserve role-aware navigation visibility and privileged-action audit flows.

## Rollout Sequence and Rollback Contract (Frozen)

1. `DEV-00046`: establish modular backend skeleton + service rename contract.
2. `DEV-00047`: split domain routers and service/repository extraction.
3. `DEV-00048`: isolate charting module and compatibility bridge.
4. `DEV-00049`: frontend shell/module split.
5. `DEV-00050`: CI quality gates and compatibility regression suite.
6. `DEV-00051`: phased cutover, observability watch, shim deprecation/removal.

Rollback policy:

- Rollback trigger examples: Sev-1 route break, auth regression, critical chart handoff failure, sustained 5xx spike.
- Rollback action: switch traffic to prior compatibility path and restore last known-good deployment artifact.
- Rollback evidence: capture failing route list, logs, and metric snapshots in debugging registry.

## Constraints and Risks

- Must preserve Docker-first runtime and compose parity at every stage.
- No unreviewed breaking API changes across migration tickets.
- High merge-conflict risk remains until monolith split is complete; enforce tight ownership by module.
- Compatibility shim overuse can create hidden debt; each shim requires explicit retirement note in `DEV-00051`.

## Operational Requirements

- Docker-first runtime remains mandatory.
- Health, metrics, and structured logs must expose both control-panel and charting module posture.
- RBAC and audit logging must remain centralized and mandatory for privileged actions.
