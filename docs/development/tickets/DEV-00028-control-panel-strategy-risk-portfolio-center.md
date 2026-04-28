# DEV-00028: Control Panel Strategy, Risk, and Portfolio Control Center

## Status

Open

## Summary

Deliver live control surfaces for strategy state, risk limits, and portfolio exposure with deterministic guardrails.

## Scope

- Strategy state board (enabled/disabled, confidence, throughput, anomalies).
- Risk limits editor (bounded configs with validation and approvals).
- Portfolio exposure dashboard:
  - symbol exposure
  - gross/net portfolio exposure
  - available equity headroom
- Kill-switch controls and policy violation forensics.

## Non-Goals

- Automated strategy optimization.
- Full PnL attribution suite.

## Acceptance Criteria

- Risk and portfolio state are visible in real time.
- Limit changes are controlled, validated, and auditable.
- Kill-switch and policy violations are actionable in-panel.

## Verification

- API and UI integration tests for constraint updates.
- Audit trail validation for all risk/portfolio config mutations.
