# Active Focus

## Objective

Execute control-panel refactor program (`DEV-00044..DEV-00051`) with contract-first sequencing and compatibility-safe migration.

## Current constraints

- Preserve Docker-first runtime simplicity.
- Keep deterministic boundaries strict (LLM advisory only).
- Maintain traceable, small-step delivery with tests and docs.
- Enforce replay determinism and fail-closed schema contracts across chain boundaries.

## Immediate next slices

1. Execute `DEV-00047` control-panel domain router split and service-layer extraction.
2. Execute `DEV-00048` control-panel charting module extraction and compatibility bridge.
3. Execute `DEV-00049` control-panel frontend app-shell restructure and UI architecture hardening.
