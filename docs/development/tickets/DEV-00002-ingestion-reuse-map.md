# DEV-00002: Ingestion Reuse Mapping (BarsFP -> NITRA)

## Status

Done

## Summary

Create a strict source-to-target reuse map for ingestion code from `../barsfp` into NITRA, classifying each candidate as `reuse-as-is`, `adapt`, or `reject`.

## Scope

- Inventory only ingestion-relevant modules/contracts/migrations/tests.
- Produce mapping with explicit target path in NITRA.
- Mark any non-essential legacy component as `reject`.

## Hard Exclusions

- Do not import monitoring-heavy stack artifacts (Loki, Tempo, Promtail, Cadvisor dashboards).
- Do not import BarsFP rulesets, process docs, or non-NITRA governance content.
- Do not import cold-path components unless required by current NITRA ingestion acceptance.

## Deliverables

1. Mapping document under `docs/development/`.
2. Reuse decision per file/module with rationale.
3. Minimal migration plan from mapping output.

## Acceptance Criteria

- Every reused item has a clear NITRA destination and owner.
- Every rejected item has a short reason.
- Mapping is sufficient to start implementation without ambiguity.

## Evidence

- Reuse map created: `docs/development/DEV-00002-reuse-map.md`
