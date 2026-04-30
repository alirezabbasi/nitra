# Active Focus

## Objective

Execute the deterministic-first Section 5 completion plan in strict priority order (P0->P8), with mandatory control-panel integration for each component before closure.

## Current constraints

- Preserve Docker-first runtime simplicity.
- Keep deterministic boundaries strict (LLM advisory only).
- Maintain traceable, small-step delivery with tests and docs.
- Enforce replay determinism and fail-closed schema contracts across chain boundaries.

## Immediate next slices

1. Start paired P0 implementation kickoff: `DEV-00068` (feeds failover policy) + `DEV-00124` (feeds ops control-panel module).
2. Continue P0 sequence through `DEV-00069`, `DEV-00070`, `DEV-00141..DEV-00143`, then raw-lake/Kafka tickets with companions.
