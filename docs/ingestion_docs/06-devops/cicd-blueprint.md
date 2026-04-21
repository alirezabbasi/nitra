# CI/CD Blueprint

## CI Requirements (Always On)

- Rust formatting, linting, unit tests.
- Container build checks for all services.
- Security scans (dependency and image).
- Documentation checks for changed architecture/ops behavior.

## CD Requirements (Production Ready)

- Build immutable image tags (`git-sha` + semantic tag).
- Push images to trusted registry.
- Promote through environments: `dev` -> `paper/staging` -> `prod`.
- Gate production promotion on quality, security, and operational checks.

## Pipeline Stages

1. Validate: lint/test/static checks.
2. Package: Docker build + SBOM + image scan.
3. Publish: signed images + release notes.
4. Deploy: Compose-based rollout per environment.
5. Verify: smoke + health + readiness + key SLO checks.
6. Rollback: automatic or operator-triggered on failed verification.
7. Closure: run `scripts/release/closure-gate.sh` and collect final sign-off records.

## Release Model

- Trunk-based or short-lived feature branches.
- Protected `main` branch.
- Conventional commits + versioned changelog.
- Release tags for deployment traceability.
