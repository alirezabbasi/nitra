# EPIC-04: Canonical Normalization and Symbol Registry

## Scope
- Normalize broker payloads into canonical schema.
- Centralize symbol, session, and timezone mapping.

## Deliverables
- Normalizer service.
- Symbol registry with versioned mappings.
- Canonical event validation rules.

## Acceptance
- Canonical event correctness and contract compliance verified in QA suite.

## Commit Slices
1. `feat(normalizer): add canonical transformation pipeline`
2. `feat(symbols): add symbol registry and mapping policies`
