# DEV-00045: Control Panel Target Architecture and Migration Contract Freeze

## Status

Done (2026-04-29)

## Summary

Define the target production architecture for `control-panel-service` and freeze migration contracts before runtime refactor begins.

## Scope

- Define backend package layout (API routers, domain services, repositories, infra clients, auth, config, observability).
- Define frontend layout (app shell, route modules, shared UI system, API client layer, state boundaries).
- Define compatibility contract for existing endpoints and UI routes.
- Define rollout sequence and fallback/rollback plan.
- Publish architecture docs + migration map.

## Deliverables

- New/updated LLD service document for `control-panel-service`.
- Refactor migration map from current monolith to target folders.
- API compatibility matrix (`current -> target` mapping).

## Acceptance Criteria

- Architecture and migration contract approved and linked by downstream tickets.
- Risks, constraints, and rollback approach documented.

## Verification

- Documentation review checklist complete.
- Contract matrix referenced by implementation tickets.

## Delivery Notes

- Expanded `control-panel-service` LLD with frozen backend/frontend ownership boundaries.
- Added explicit compatibility header contract, route/UI guarantees, and rollout/rollback policy.
- Published migration map and API compatibility matrix:
  - `docs/design/ingestion/07-devdocs/04-lld-services/control-panel-service-migration-map.md`
- Added executable verification pack `tests/dev-0045/run.sh` and `make test-dev-0045`.
