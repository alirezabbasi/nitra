# DEV-00039: Signal Engine Deterministic Scorer and Explainability Baseline

## Status

Open

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
