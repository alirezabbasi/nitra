# DEV-00043: Journal Evidence Fabric and Incident Bundle Export

## Status

Done

## Summary

Elevate journal/audit layer into first-class evidence fabric with end-to-end correlation and exportable incident bundles.

## Scope

- Define canonical audit taxonomy across second chain.
- Ensure correlation IDs/lineage from bars -> structure -> features -> signal -> risk -> execution -> portfolio.
- Implement incident evidence bundle export contract for operator/runbook workflows.
- Add retention/indexing guidance for forensic query performance.

## Non-Goals

- External SIEM replacement.
- Full observability platform redesign.

## Acceptance Criteria

- Any order/decision path can be reconstructed end-to-end.
- Incident bundles contain sufficient artifacts for RCA/compliance review.
- Audit taxonomy is stable and versioned.

## Verification

- End-to-end lineage reconstruction tests.
- Incident bundle export validation checks.
- Audit taxonomy conformance tests.

## Delivery Notes

- Added incident evidence bundle persistence contract: `infra/timescaledb/init/017_incident_evidence_bundle.sql`.
- Extended execution-gateway audit payloads with canonical taxonomy metadata via `EXEC_AUDIT_TAXONOMY_VERSION`.
- Added lineage/correlation propagation in execution intent parsing and audit persistence.
- Added automatic incident bundle export on rejected/terminal execution outcomes.
- Added verification pack `tests/dev-0043/run.sh` and `make test-dev-0043`.
