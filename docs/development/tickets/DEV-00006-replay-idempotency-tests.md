# DEV-00006: Replay and Idempotency Verification Tests

## Status

Open

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

