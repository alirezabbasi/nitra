# Active Focus

## Objective

Execute second-chain deterministic hardening (`structure -> feature -> signal -> risk -> execution -> portfolio -> journal`) with contract-first sequencing.

## Current constraints

- Preserve Docker-first runtime simplicity.
- Keep deterministic boundaries strict (LLM advisory only).
- Maintain traceable, small-step delivery with tests and docs.
- Enforce replay determinism and fail-closed schema contracts across chain boundaries.

## Immediate next slices

1. `DEV-00042` portfolio authoritative reconciliation and state invariants.
2. `DEV-00043` journal/audit evidence fabric and incident bundle export.
3. Start control-panel refactor stream `DEV-00044` after second-chain closure.
