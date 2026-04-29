# DEV-00040: Risk Policy Expansion and Decision Traceability Hardening

## Status

Done (2026-04-29)

## Summary

Expand risk policy coverage and strengthen decision traceability so every approval/rejection is deterministic and forensically explainable.

## Scope

- Add richer policy controls (exposure, drawdown, confidence, regime, kill-switch variants).
- Emit canonical policy IDs/reason codes in every decision event.
- Persist policy evaluation traces for post-incident diagnostics.
- Add stress/regression suites for policy interactions.

## Non-Goals

- Portfolio accounting redesign.
- Broker adapter redesign.

## Acceptance Criteria

- All risk decisions carry policy trace metadata.
- Policy interactions are deterministic under replay.
- Stress scenarios pass with expected fail-closed behavior.

## Verification

- Risk policy regression suite.
- Decision trace persistence checks.
- Replay determinism checks for risk outcomes.

## Delivery Evidence

- Expanded deterministic risk policy coverage in `services/risk-engine/src/main.rs`:
  - added volatility, conflict-score, and strict kill-switch variant checks,
  - added canonical policy IDs (`RISK-*`) and policy-hit lists per decision.
- Added decision traceability contract:
  - risk events now include `policy_bundle_id`, `policy_hits`, and `evaluation_trace`.
  - `risk_decision_log` now persists `policy_hits` + `evaluation_trace`.
- Added schema migration:
  - `infra/timescaledb/init/015_risk_policy_trace.sql`
- Added stress/regression verification:
  - `tests/dev-0040/run.sh`
  - `make test-dev-0040`
