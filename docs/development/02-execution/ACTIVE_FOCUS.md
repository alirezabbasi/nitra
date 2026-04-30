# Active Focus

## Objective

Execute the deterministic-first Section 5 completion plan in strict priority order (P0->P8), with mandatory control-panel integration for each component before closure.

## Current constraints

- Preserve Docker-first runtime simplicity.
- Keep deterministic boundaries strict (LLM advisory only).
- Maintain traceable, small-step delivery with tests and docs.
- Enforce replay determinism and fail-closed schema contracts across chain boundaries.

## Immediate next slices

1. Start Priority 0 only: `DEV-00065`, `DEV-00068..DEV-00076`, `DEV-00141..DEV-00143` with control-panel companions `DEV-00124..DEV-00126`.
2. Block advancement to P2+ until P0 and P1 deterministic gates are complete and evidenced.
