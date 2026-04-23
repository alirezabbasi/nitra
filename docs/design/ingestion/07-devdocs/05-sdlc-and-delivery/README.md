# SDLC and Delivery Guide

## Canonical Lifecycle

1. Design alignment with HLD and LLD.
2. Implementation in scoped change set.
3. Tests (unit/integration/epic step pack).
4. Docs updates (subject docs + 07-devdocs if developer workflow changes).
5. Subject-separated commits.
6. Release readiness checks.

## Commit Discipline

Follow strict step-based commit rules from `ruleset.md`.

Typical grouping:

1. code and config
2. tests
3. docs

## Definition of Done

A change is done only when:

- runtime behavior implemented,
- tests added/updated and executed,
- docs updated,
- changes committed in traceable groups.
