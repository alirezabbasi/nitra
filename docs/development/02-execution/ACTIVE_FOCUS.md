# Active Focus

## Objective

Execute `DEV-00064` as the first post-control-panel roadmap slice with deterministic feature-platform shadow-readiness scope.

## Current constraints

- Preserve Docker-first runtime simplicity.
- Keep deterministic boundaries strict (LLM advisory only).
- Maintain traceable, small-step delivery with tests and docs.
- Enforce replay determinism and fail-closed schema contracts across chain boundaries.

## Immediate next slices

1. Implement `DEV-00064` contract artifacts for feature shadow snapshots and replay/live parity checks.
2. Add follow-up implementation ticket(s) that wire shadow-readiness observability into runtime endpoints without changing live execution decisions.
