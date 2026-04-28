# Active Focus

## Objective

Transition from ingestion-only completion into full-platform, HLD-aligned incremental delivery without context drift.

## Current constraints

- Preserve Docker-first runtime simplicity.
- Keep deterministic boundaries strict (LLM advisory only).
- Maintain traceable, small-step delivery with tests and docs.

## Immediate next slices

1. Implement broker-venue adapter layer for `execution-gateway` (submit/amend/cancel + ack/fill mapping).
2. Add deterministic portfolio-state baseline to support richer risk/execution constraints.
3. Expand audit/reconciliation workflows for post-trade forensics and operator runbooks.
