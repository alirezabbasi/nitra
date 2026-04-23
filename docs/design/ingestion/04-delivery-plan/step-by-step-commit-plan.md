# Step-by-Step Commit Plan

This is the recommended commit sequence. Each commit should be small, reviewable, and test-backed.

1. `chore(repo): initialize barsfp monorepo and baseline docs`
2. `docs(architecture): add target architecture and domain boundaries`
3. `build(rust): add workspace, crates, and shared domain models`
4. `infra(dev): add docker compose for redpanda/timescale/clickhouse/minio/grafana`
5. `feat(stream): define topic contracts and schema versioning`
6. `feat(connector): implement broker-1 raw ingestion service`
7. `feat(normalizer): add canonical normalization pipeline`
8. `feat(bars): add deterministic 1s/1m aggregation and timescale writes`
9. `feat(gaps): add coverage tracker and gap detector`
10. `feat(backfill): add missing-only backfill with replay`
11. `feat(archive): add parquet archive writer and manifest checkpoints`
12. `feat(cold): add clickhouse loaders and cold query model`
13. `feat(risk): implement pre-trade risk gateway`
14. `feat(execution): implement OMS state machine and reconciliation`
15. `feat(obs): add metrics/logs/traces dashboards and alert rules`
16. `feat(rollout): add paper-run controls and micro-live gates`
17. `docs(runbooks): add operational runbooks and incident drills`
18. `chore(release): add closure audit and known-limitations register`

## Commit Rules

- One logical unit per commit.
- Include tests or explicit QA evidence in same commit when possible.
- Never mix infra refactors with feature behavior changes in one commit.
- Tag release-gate commits with evidence links in commit body.
