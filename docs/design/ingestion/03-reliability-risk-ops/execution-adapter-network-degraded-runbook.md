# Execution Adapter Degraded-Network Runbook (DEV-00022)

## Purpose

Provide deterministic operator guidance when broker adapter calls fail due to DNS/connectivity/timeout/upstream degradation.

## Failure classes

- `dns_resolution`
- `connect_timeout`
- `connect_error`
- `io_timeout`
- `upstream_5xx`
- `upstream_4xx`
- `request_error`

## Immediate triage

1. Check `execution_order_journal.execution_metadata` for:
   - `adapter_failure_class`
   - `adapter_attempts`
   - `adapter_terminal`
2. Check `exec.reconciliation_issue.v1` events for:
   - `issue = adapter_terminal_failure` or `adapter_command_failure`
   - failure class + reason
3. Check `audit_event_log` entries for `order_submit_rejected` or `order_command`.

## Deterministic safety policy

- Retry is bounded by `EXEC_BROKER_RETRY_MAX_ATTEMPTS`.
- Backoff is bounded by `EXEC_BROKER_RETRY_BACKOFF_CAP_MS`.
- Terminal failures are fail-closed and journaled.
- Cooldown `EXEC_BROKER_DEGRADED_COOLDOWN_MS` reduces retry storm pressure.

## Evidence checklist

Capture and attach:

1. Active execution-gateway env policy values (`EXEC_BROKER_*`).
2. Recent `execution_order_journal` rows with adapter metadata.
3. Recent reconciliation issue events with failure class.
4. Audit log entries for impacted order IDs.
5. Time window and venue/symbol scope of impact.

## Recovery closure criteria

- New adapter calls succeed with `failure_class = null`.
- Reconciliation queue stabilizes for impacted markets.
- No sustained retry-driven error burst in logs.
