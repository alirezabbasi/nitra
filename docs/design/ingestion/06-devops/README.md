# DevOps Plan (Mandatory)

This folder defines the enforceable DevOps operating model for BarsFP.

It implements `ruleset.md` requirements for:
- Docker-first runtime.
- Server portability with `docker compose up -d` from project root.
- CI/CD readiness for production rollout and continuous development.

## Documents

- `deployment-contract.md`
- `docker-compose-standards.md`
- `server-bootstrap.md`
- `cicd-blueprint.md`
- `security-secrets.md`
- `operations-backup-dr.md`
- `observability-stack.md`
- `release-closure-gate.md`
- `implementation-checklist.md`

## Compliance Rule

Implementation work that changes runtime/build/deploy/operations behavior must update the relevant file in this folder in the same change set.
