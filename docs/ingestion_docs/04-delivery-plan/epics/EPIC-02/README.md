# EPIC-02: Redpanda Backbone

## Scope
- Create topic strategy, retention policies, replay and DLQ paths.
- Define schema version lifecycle.

## Deliverables
- Topic bootstrap scripts.
- Producer/consumer conventions.
- Retry metadata and DLQ contracts.

## Acceptance
- Fault-injection tests confirm no silent loss.
- Replay restores state deterministically.

## Commit Slices
1. `infra(stream): add redpanda bootstrap and topic config`
2. `feat(stream): add retry/dlq/replay contract libraries`
