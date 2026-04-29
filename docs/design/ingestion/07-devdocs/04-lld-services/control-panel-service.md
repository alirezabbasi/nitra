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

## Migration Contract

- Keep current endpoint behavior while internals are split.
- Preserve control-panel route entrypoint (`/control-panel`).
- Preserve chart surface routes used by operator workflows.
- Use compatibility headers and explicit deprecation schedule for any path relocation.

## Operational Requirements

- Docker-first runtime remains mandatory.
- Health, metrics, and structured logs must expose both control-panel and charting module posture.
- RBAC and audit logging must remain centralized and mandatory for privileged actions.
