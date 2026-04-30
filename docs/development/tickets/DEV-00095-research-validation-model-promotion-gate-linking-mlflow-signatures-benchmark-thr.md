# DEV-00095: Research/Validation - model promotion gate + MLflow lineage/comparison hardening.

## Status

Planned

## Goal

Define and deliver: deterministic model-promotion governance including MLflow signature validation, benchmark threshold enforcement, lineage evidence, and model-version comparison controls.

## Scope

- Promotion gate workflow with explicit approval and rollback contracts.
- MLflow lineage and run/model comparison hardening required for promotion evidence.
- Signature/schema validation checks bound to promotion decision path.
- Test/documentation updates for gate reproducibility.

## Non-Goals

- Feature-platform computation contracts (`DEV-00086..DEV-00090`).
- Online inference serving topology (`DEV-00096..DEV-00099`).

## Acceptance Criteria

- Promotion decisions require passing benchmark thresholds plus valid MLflow lineage/signature evidence.
- Model comparison artifacts are available and reproducible for approval audit.
- Deterministic tests validate rejection paths for incomplete/inconsistent evidence.

## Verification

- Run the relevant `make test-*` target(s) for this scope.
- `make enforce-section-5-1`
- `make session-bootstrap`

## Notes

- This ticket file was generated to restore ticket-registry integrity from `KANBAN.md`.
