# DEV-00032: Control Panel Research, Backtesting, and Model Ops Center

## Status

Open

## Summary

Create a governance-first workspace for dataset lineage, experiment tracking, backtest runs, and model promotion states.

## Scope

- Dataset registry and lineage view.
- Backtest run launcher/status/history.
- MLflow experiment and model registry integration surfaces.
- Promotion readiness gates and approval workflow.

## Non-Goals

- Notebook IDE replacement.
- Model training pipeline rewrite.

## Acceptance Criteria

- Research/model lifecycle states are transparent and queryable.
- Promotion decisions are explicit and auditable.
- Backtest outcomes are reproducible and linked to datasets/models.

## Verification

- API contract tests for dataset/backtest/model views.
- Promotion audit trail validation.
