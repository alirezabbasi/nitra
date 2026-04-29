# Active Focus

## Objective

Execute control-panel refactor program (`DEV-00044..DEV-00051`) with contract-first sequencing and compatibility-safe migration.

## Current constraints

- Preserve Docker-first runtime simplicity.
- Keep deterministic boundaries strict (LLM advisory only).
- Maintain traceable, small-step delivery with tests and docs.
- Enforce replay determinism and fail-closed schema contracts across chain boundaries.

## Immediate next slices

1. Execute `DEV-00050` control-panel refactor quality gates and CI readiness.
2. Execute `DEV-00051` control-panel refactor rollout, cutover, and deprecation closure.
3. Expand reconciliation/runbook evidence capture for live adapter behavior.
