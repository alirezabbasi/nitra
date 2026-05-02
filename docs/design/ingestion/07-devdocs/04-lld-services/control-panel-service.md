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
    control-panel.html
    app/
      control-panel.js
    modules/
      README.md
    components/
      format.js
    services/
      api-client.js
    state/
      preferences.js
    styles/
      control-panel.css
  dist/
    control-panel.html
    app/control-panel.js
    styles/control-panel.css
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

## DEV-00046 Foundation Snapshot

- Runtime service key in compose: `control-panel`.
- Backend bootstrap entrypoint: `services/control-panel/app/main.py`.
- Compatibility mode: legacy charting app mounted behind new control-panel boundary until domain/router extraction is complete.

## DEV-00047 Domain Split Snapshot

- Domain routers extracted under `services/control-panel/app/api/routers/` for:
  - `auth_session`, `overview`, `ingestion`, `risk_portfolio`, `execution`, `ops`, `research`, `config`, `search`.
- Service layer bridge introduced at `services/control-panel/app/services/control_panel/legacy_proxy.py`.
- Shared legacy loader centralized at `services/control-panel/app/core/legacy_bridge.py`.
- Compatibility preserved by router-first dispatch with legacy fallback mount for non-extracted paths.

## DEV-00049 Frontend Shell Snapshot

- Frontend single-file runtime has been split into source-managed assets under `services/control-panel/frontend/src`.
- Runtime artifact path is now `services/control-panel/frontend/dist`, built via:
  - `scripts/frontend/build_control_panel_frontend.sh`
- Control-panel service now serves:
  - `/control-panel` -> `frontend/dist/control-panel.html`
  - `/control-panel-assets/*` -> `frontend/dist/*`
- Legacy charting mount remains for non-extracted routes and full-chart embed continuity.

## DEV-00050 Quality Gate Snapshot

- Added deterministic quality gate pack: `tests/dev-0050/run.sh`.
- Added CI-ready aggregate command:
  - `scripts/ci/control_panel_refactor_quality_gate.sh`
- Gate scope includes:
  - backend compile and router-hygiene checks,
  - frontend build/parity checks (`src -> dist`),
  - compatibility contract regression (`dev-0048`, `dev-0049`),
  - native + compatibility route smoke checks.

## DEV-00051 Cutover Snapshot

- Control-panel charting migration is now in `cutover-closed` phase.
- Legacy charting alias routes are retired; only `/api/v1/charting/*` remains canonical.
- Migration state visibility endpoint added:
  - `/api/v1/control-panel/migration/status`
- Rollout and rollback operations are documented in:
  - `docs/design/ingestion/06-devops/control-panel-rollout-cutover-runbook.md`
  - `docs/design/ingestion/06-devops/control-panel-deprecation-closure-report.md`

## DEV-00124 Feeds Ops Snapshot

- Ingestion operations module includes connector failover policy controls.
- Control-panel API contract:
  - `GET /api/v1/control-panel/ingestion`
    - returns connector status, recovery queues, and failover policy/runtime sections.
  - `POST /api/v1/control-panel/ingestion/failover-policy`
    - role-gated policy updates with justification and audit logging.
- UI contract:
  - ingestion workspace renders per-venue failover policy table + guarded update form.

## DEV-00069 + DEV-00141 Feeds Reliability Ops

- Ingestion workspace now includes paired policy surfaces for session reliability:
  - credential/session lifecycle policy module (`DEV-00069`)
  - websocket/session runtime policy module (`DEV-00141`)
- Control-panel API contract additions:
  - `POST /api/v1/control-panel/ingestion/session-policy`
  - `POST /api/v1/control-panel/ingestion/ws-policy`
- `GET /api/v1/control-panel/ingestion` now includes:
  - `session_policies`, `session_runtime`
  - `ws_policies`, `ws_runtime`
- Both mutation endpoints require operator role minimum, justification, and audit trail records.

## DEV-00070 + DEV-00142 Feed Quality + Throttling Ops

- Ingestion workspace now includes:
  - `Feed Quality SLA` table for per-market latency/drop/sequence/heartbeat posture.
  - `Adaptive Rate-Limit Policy` table and guarded update form.
- Control-panel API contract additions:
  - `POST /api/v1/control-panel/ingestion/rate-limit-policy`
- `GET /api/v1/control-panel/ingestion` now includes:
  - `connector_feed_sla`
  - `rate_limit_policies`, `rate_limit_runtime`
- Mutation endpoint requires operator role minimum, justification, and audit trail records.

## DEV-00143 Raw Capture Ops

- Ingestion workspace includes `Raw Capture Provenance (Recent)` operator table.
- `GET /api/v1/control-panel/ingestion` now includes:
  - `raw_capture_recent`
  - `metrics.raw_capture_rows_24h`
  - `metrics.sequence_anomalies_24h`
- Surface intent:
  - verify untouched inbound message capture continuity,
  - triage sequence-provenance anomalies (`gap`, `out_of_order`, `duplicate`) quickly from control panel.

## DEV-00071 Raw Lake Ops

- Ingestion workspace includes `Raw Lake Object Manifest (Recent)` operator table.
- `GET /api/v1/control-panel/ingestion` now includes:
  - `raw_lake_manifest_recent`
  - `metrics.raw_lake_objects_24h`
- Surface intent:
  - verify canonical partition/object-key progression,
  - confirm replay-grade offset range provenance per object partition window.

## DEV-00072 Replay Manifest Ops

- Ingestion workspace includes `Replay Manifest Index Builder` controls and `replay manifest recent` table.
- Control-panel API contract addition:
  - `POST /api/v1/control-panel/ingestion/raw-lake/replay-manifest`
- `GET /api/v1/control-panel/ingestion` now includes:
  - `replay_manifest_recent`

## DEV-00073 Raw Lake Retention Ops

- Ingestion workspace now includes:
  - `Raw Lake Retention/Tiering Policy` table + guarded update form.
  - `Restore Drill Evidence` log form + recent drill table.
- Control-panel API contract additions:
  - `POST /api/v1/control-panel/ingestion/raw-lake/retention-policy`
  - `POST /api/v1/control-panel/ingestion/raw-lake/restore-drill`
- `GET /api/v1/control-panel/ingestion` now includes:
  - `raw_lake_retention_policies`
  - `raw_lake_restore_drills`
- Surface intent:
  - build deterministic range-scoped replay object selections,
  - persist checksum-verifiable manifest indices for reproducible replay runs.
