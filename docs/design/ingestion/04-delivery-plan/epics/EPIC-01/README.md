# EPIC-01: Rust Workspace Foundation

## Scope
- Build monorepo Rust workspace and shared crates.
- Establish CI compile/test baseline.

## Deliverables
- `crates/domain`, `crates/contracts`, `services/*` skeletons.
- Cargo workspace config and lint/test workflow.

## Acceptance
- All service crates compile in CI.
- Shared contract crate consumed by all services.

## Commit Slices
1. `build(rust): create workspace and shared crates`
2. `ci(rust): add format/lint/test jobs`
