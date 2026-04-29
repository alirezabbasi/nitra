# DEV-00022: Execution Adapter Network Resilience

## Status

Done (2026-04-29)

## Summary

Harden `execution-gateway` broker adapter behavior for DNS/connectivity/runtime failures so execution transitions remain deterministic, observable, and operationally recoverable under degraded network conditions.

## Scope

- Define explicit network failure policy for broker submit/amend/cancel calls:
  - DNS resolution failures
  - TCP connect timeouts
  - read/write timeouts
  - transient upstream `5xx` responses
- Add bounded retry/backoff contract with deterministic limits and terminal outcomes.
- Introduce failure classification in execution metadata/audit payloads for operator triage.
- Add degraded-mode safeguards to prevent uncontrolled retry storms.
- Add operator-facing runbook guidance and evidence checklist for degraded network events.

## Non-Goals

- Broker-specific auth/session lifecycle redesign.
- Full circuit-breaker platform rollout across all services.
- Portfolio/PnL accounting behavior changes.

## Architecture Alignment

- LLD section 12 execution gateway lifecycle and reconciliation requirements.
- LLD section 15 audit/observability traceability requirements.
- HLD deterministic execution and fail-closed operational posture.

## Proposed Acceptance Criteria

- Retry/backoff policy is deterministic, bounded, and configured via documented env contract.
- Terminal adapter failures are persisted with explicit failure class and reason.
- Reconciliation issue events include actionable network-failure context.
- Dedicated test pack validates timeout/DNS/5xx classification and retry bounds.
- Memory/kanban/docs synchronized with closure evidence.

## Expected Artifacts

- `services/execution-gateway/src/main.rs` (resilience logic + classification)
- `docker-compose.yml` (new env contract)
- `docs/design/ingestion/07-devdocs/01-development-environment/ingestion-service-env.md`
- `docs/design/nitra_system_lld/01_service_catalog.md`
- `tests/dev-0022/run.sh` + Make target
- optional schema extension if additional persistence fields are required

## Verification Plan

- `cargo fmt --manifest-path services/execution-gateway/Cargo.toml`
- `CARGO_TARGET_DIR=/tmp/nitra-execution-gateway-target cargo check --offline --manifest-path services/execution-gateway/Cargo.toml`
- `CARGO_TARGET_DIR=/tmp/nitra-execution-gateway-target cargo test --offline --manifest-path services/execution-gateway/Cargo.toml`
- `tests/dev-0022/run.sh`
- `make enforce-section-5-1`
- `make session-bootstrap`
