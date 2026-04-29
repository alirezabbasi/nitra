# DEV-00039: Signal Engine Deterministic Scorer and Explainability Baseline

## Status

Done (2026-04-29)

## Summary

Build deterministic signal scorer that converts feature snapshots into explainable scoring outputs with strict reproducibility.

## Scope

- Define deterministic scoring contract and threshold policy.
- Emit scored signal event with reason codes and feature references.
- Add calibration/backtest harness for score behavior validation.
- Add strict version pinning for scorer config and output metadata.

## Non-Goals

- LLM advisory signal generation.
- Automated model retraining workflows.

## Acceptance Criteria

- Identical feature snapshots produce identical score outputs.
- Signal payload includes traceable reason codes.
- Calibration harness validates expected score distributions.

## Verification

- Scorer determinism tests.
- Explainability payload contract checks.
- Calibration/backtest report artifacts.

## Delivery Evidence

- Implemented deterministic signal scorer baseline in:
  - `services/inference-gateway/app.py`
- Added scored-signal persistence contract:
  - `infra/timescaledb/init/014_signal_score_log.sql`
- Runtime wiring updated:
  - `docker-compose.yml` signal env contract + runtime command
  - `docker-compose.yml` risk input switched to `decision.signal_scored.v1`
- Added verification pack:
  - `tests/dev-0039/run.sh`
  - `tests/dev-0039/unit/test_signal_logic.py`
  - `make test-dev-0039`
- Added LLD/env docs:
  - `docs/design/ingestion/07-devdocs/04-lld-services/signal-engine.md`
  - `docs/design/ingestion/07-devdocs/01-development-environment/ingestion-service-env.md`
