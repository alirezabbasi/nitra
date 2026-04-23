# Design Documentation Map

## Purpose

This folder defines architecture authority for NITRA.

## Authoritative documents

- `nitra_system_hld.md`: primary project HLD used for implementation tracking.
- `AI-enabled_trading_decision_platform.md`: strategic architecture baseline and principle source.
- `nitra_system_lld/`: implementation-level LLD pack.
- `ingestion/`: ingestion-domain architecture, data-platform, DevOps, and LLD documentation.

## Supporting documents

- `ARCHITECTURE_DECISIONS.md`: architecture decisions and rationale.
- `NEXT_STEPS.md`: suggested build order and sequencing guidance.
- `ingestion/ruleset.md`: domain operating ruleset for ingestion scope.

## Precedence model

If two design docs overlap:

1. `nitra_system_hld.md` is the execution-facing architecture map.
2. `AI-enabled_trading_decision_platform.md` is the strategic baseline and principle guardrail.
3. Divergence must be resolved through explicit updates and/or ADR entries.
