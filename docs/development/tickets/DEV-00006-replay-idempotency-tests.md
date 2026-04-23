# DEV-00006: Replay and Idempotency Verification Tests

## Status

Done

## Summary

Add step-scoped tests in NITRA to verify explicit commit lifecycle, replay safety, and duplicate-side-effect prevention in ingestion services.

## Scope

- Add tests under `tests/` for:
  - manual consumer commit behavior
  - duplicate message handling via ledger
  - replay-safe side effects for key ingestion stages
- Provide automated run entrypoint for this verification pack.

## Hard Exclusions

- No broad test imports that verify components not wired into NITRA.
- No flaky environment-dependent checks without deterministic assertions.

## Deliverables

1. Step-scoped test pack and run script.
2. Minimal evidence output format for pass/fail checks.
3. Documentation of what replay/idempotency is guaranteed.

## Acceptance Criteria

- Duplicate injection does not create duplicate side effects.
- No silent message loss in tested failure/replay scenarios.
- Tests are runnable in dev setup and support pre-commit verification.

## Evidence

- Test pack: `tests/dev-00006/run.sh`
- Optional duplicate integration drill: `tests/dev-00006/run-integration.sh`
- Runtime guards implemented in:
  - `services/market-normalization/app.py`
  - `services/bar-aggregation/app.py`
  - `services/gap-detection/app.py`
  - `services/backfill-worker/app.py`
- Guarantee doc: `docs/design/ingestion/02-data-platform/stream-replay-idempotency.md`
