# NITRA Ingestion Domain Documentation

This folder is the canonical ingestion-domain documentation set for NITRA.

## Required first reads

1. `docs/design/ingestion/ruleset.md`
2. `docs/design/nitra_system_hld.md`
3. `docs/design/AI-enabled_trading_decision_platform.md`
4. `docs/design/ingestion/07-devdocs/README.md`

## Structure

- `00-source-review/`: source analysis and migration context.
- `01-architecture/`: ingestion architecture boundaries.
- `02-data-platform/`: contracts, schema, stream reliability, replay, storage.
- `03-reliability-risk-ops/`: runbooks, controls, SLO/operability docs.
- `04-delivery-plan/`: roadmap, epics, closure records.
- `05-git-workflow/`: delivery and release workflow docs.
- `06-devops/`: deployment and operations standards.
- `07-devdocs/`: onboarding and LLD/dev implementation guides.
- `bugs/`: ingestion bug registry.

## Notes

- Some documents retain legacy BarsFP migration context; NITRA behavior and rulesets take precedence.
- This folder should not duplicate project-wide execution tracking from `docs/development/`.
