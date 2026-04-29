# DEV-00047: Control Panel Domain Router Split and Service-Layer Extraction

## Status

Proposed (2026-04-29)

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
