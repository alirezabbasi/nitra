# DEV-00043: Journal Evidence Fabric and Incident Bundle Export

## Status

Open

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
