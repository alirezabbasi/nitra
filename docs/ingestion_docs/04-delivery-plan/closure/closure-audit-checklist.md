# Closure Audit Checklist

## Quality Gates

- [ ] `cargo fmt --all --check`
- [ ] `cargo clippy --workspace --all-targets -- -D warnings`
- [ ] `cargo test --workspace`
- [ ] `./tests/run-all.sh`
- [ ] `docker compose config`

## Rollout Governance

- [ ] Paper evidence window complete.
- [ ] Micro-live checklist reviewed and approved.
- [ ] Emergency procedure drill evidence attached.
- [ ] Rollback owner confirmed.

## Reliability and Risk

- [ ] No open critical incidents.
- [ ] Risk and OMS anomaly alerts reviewed.
- [ ] Reconciliation anomalies explained and closed.

## Documentation and Sign-Off

- [ ] Final sign-off file completed.
- [ ] Known limitations register updated.
- [ ] EPIC-11 implementation log updated with verification evidence.

## Gate Command

Run:

```bash
scripts/release/closure-gate.sh --require-clean
```
