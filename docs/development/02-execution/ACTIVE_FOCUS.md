# Active Focus

## Objective

Execute second-chain deterministic hardening (`structure -> feature -> signal -> risk -> execution -> portfolio -> journal`) with contract-first sequencing.

## Current constraints

- Preserve Docker-first runtime simplicity.
- Keep deterministic boundaries strict (LLM advisory only).
- Maintain traceable, small-step delivery with tests and docs.
- Enforce replay determinism and fail-closed schema contracts across chain boundaries.

## Immediate next slices

1. `DEV-00037` structure-engine production deterministic hardening.
2. `DEV-00038` feature-service deterministic baseline and point-in-time integrity.
3. `DEV-00039` signal-engine deterministic scorer and explainability baseline.
