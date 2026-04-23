# Release Closure Gate

## Purpose

Define the mandatory closure validation command before final sign-off.

## Command

```bash
scripts/release/closure-gate.sh --require-clean
```

## Quick Mode

For rapid local verification:

```bash
scripts/release/closure-gate.sh --quick
```

## Gate Outputs

A passing run confirms:

1. Required runbook and closure docs exist.
2. Compose runtime contract is valid.
3. Quality checks pass (format/lint/test scope by mode).
4. EPIC test coverage is green.

## Required Evidence

Attach to release record:

- Closure gate output log.
- Completed `docs/04-delivery-plan/closure/final-signoff.md`.
- Updated `docs/04-delivery-plan/closure/known-limitations-register.md`.
