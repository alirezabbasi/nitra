# DEV-00047: Control Panel Domain Router Split and Service-Layer Extraction

## Status

Done (2026-04-29)

## Summary

Extract control-panel APIs from monolithic route handlers into domain routers with explicit service and repository layers.

## Scope

- Split endpoints into routers by domain:
  - `overview`, `ingestion`, `risk_portfolio`, `execution`, `ops`, `research`, `config`, `search`, `auth_session`.
- Move SQL and business logic out of route functions into service/repository modules.
- Standardize request/response models and error handling.
- Centralize auth/RBAC checks and audit logging utilities.

## Acceptance Criteria

- No domain route contains large inline SQL/business logic blocks.
- Shared policies (RBAC, audit, validation) are reusable primitives.
- Endpoint behavior remains parity-compatible.

## Verification

- API regression tests for each domain endpoint group.
- Role/permission contract tests.

## Delivery Notes

- Added domain routers under `services/control-panel/app/api/routers/`:
  - `auth_session.py`, `overview.py`, `ingestion.py`, `risk_portfolio.py`, `execution.py`, `ops.py`, `research.py`, `config.py`, `search.py`.
- Added service-layer extraction bridge:
  - `services/control-panel/app/services/control_panel/legacy_proxy.py`.
- Added centralized legacy bridge loader:
  - `services/control-panel/app/core/legacy_bridge.py`.
- Updated `services/control-panel/app/main.py` router composition to mount extracted domain routers first, with legacy app retained for compatibility fallback.
- Added verification pack `tests/dev-0047/run.sh` and `make test-dev-0047`.
