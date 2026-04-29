# Active Focus

## Objective

Execute a production-grade control-panel service refactor to eliminate monolithic FastAPI/HTML architecture while preserving current operator workflows.

## Current constraints

- Preserve Docker-first runtime simplicity.
- Keep deterministic boundaries strict (LLM advisory only).
- Maintain traceable, small-step delivery with tests and docs.
- Keep API/UI compatibility during phased migration.

## Immediate next slices

1. `DEV-00044` control-panel service refactor program kickoff and architecture freeze.
2. `DEV-00045` target architecture and migration contract publication.
3. `DEV-00046` backend modularization foundation and service boundary rename.
