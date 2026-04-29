# Active Focus

## Objective

Execute second-chain deterministic hardening (`structure -> feature -> signal -> risk -> execution -> portfolio -> journal`) with contract-first sequencing.

## Current constraints

- Preserve Docker-first runtime simplicity.
- Keep deterministic boundaries strict (LLM advisory only).
- Maintain traceable, small-step delivery with tests and docs.
- Enforce replay determinism and fail-closed schema contracts across chain boundaries.

## Immediate next slices

1. `DEV-00040` risk policy expansion and decision traceability hardening.
2. `DEV-00041` execution lifecycle controls and reconciliation SLA hardening.
3. `DEV-00042` portfolio authoritative reconciliation and state invariants.
