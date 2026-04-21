# EPIC-22: Reference Data and Trading Session Model

## Scope
- Introduce first-class reference entities for instruments and sessions.
- Enforce symbol/session validation boundaries in runtime paths.

## Deliverables
- `instrument` and `session_calendar` schema, loader jobs, and validation contracts.
- Normalizer and downstream engines integration with session guards.
- Data quality checks for unknown instrument/session cases.

## Acceptance
- No event reaches canonical pipeline without valid instrument/session context.

## Commit Slices
1. `feat(refdata): add instrument and session calendar schema`
2. `feat(normalizer): enforce instrument and session validation`
3. `test(refdata): add reference-data quality and guard tests`
