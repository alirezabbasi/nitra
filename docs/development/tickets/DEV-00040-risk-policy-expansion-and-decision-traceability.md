# DEV-00040: Risk Policy Expansion and Decision Traceability Hardening

## Status

Open

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
