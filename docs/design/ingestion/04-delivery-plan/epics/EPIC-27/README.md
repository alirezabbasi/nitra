# EPIC-27: Research, Model, and Prompt Governance

## Scope
- Introduce durable governance entities for model and prompt lifecycle.
- Close HLD Section 6 gaps for `research_run`, `model_version`, `prompt_version`.

## Deliverables
- Schema for reproducible research runs and versioned model/prompt artifacts.
- Promotion/rollback state machine and approval metadata.
- Runtime linkage from live decisions to active model/prompt versions.

## Acceptance
- Every production decision resolves to exact research run, model version, and prompt version.

## Commit Slices
1. `feat(mlops): add research_run model_version prompt_version schema`
2. `feat(mlops): add version promotion rollback workflow`
3. `test(mlops): add runtime-to-version traceability checks`
