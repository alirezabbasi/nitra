# Known Limitations Register

## Purpose

Track accepted limitations at closure time with explicit ownership and follow-up plans.

## Entries

| ID | Area | Limitation | Impact | Mitigation | Owner | Target Fix Release |
|---|---|---|---|---|---|---|
| KL-001 | Execution | OMS currently uses simulated broker order IDs in baseline workflow. | Live broker adapter behavior not fully exercised. | Keep micro-live in limited scope and validate broker adapter before full prod. | Engineering | Next release after broker adapter hardening |
| KL-002 | Observability | Trace ingestion is provisioned (Tempo) but end-to-end application spans are not yet emitted by all services. | Root-cause analysis can rely more on logs/metrics than traces. | Add OpenTelemetry spans incrementally per critical service. | Platform | Next observability hardening sprint |
| KL-003 | Operations | Closure gate script runs local quality gates and doc checks, but CI artifact signing is still pending final pipeline integration. | Final release attestation remains partially manual. | Complete CI signing and provenance workflow in production rollout phase. | DevOps | Production pipeline milestone |

## Review Rule

This register must be reviewed and updated at every release closure gate.
