# Developer Guides (Canonical)

This folder is the canonical developer handbook for onboarding and implementation.
It complements project HLDs in:
- [nitra_system_hld.md](../../nitra_system_hld.md)
- [AI-enabled_trading_decision_platform.md](../../AI-enabled_trading_decision_platform.md)
with practical low-level design (LLD) and delivery guidance.

## Purpose

- Onboard new developers to full-stack project ownership.
- Define LLD contracts and implementation boundaries.
- Standardize SDLC, tests, and commit behavior.
- Keep engineering decisions traceable to HLD.

## Structure

- `00-onboarding/`: first-day and first-week onboarding path.
- `01-development-environment/`: local environment, Docker, and validation workflow.
- `02-lld-architecture/`: service-level architecture and runtime interactions.
- `03-lld-data-model/`: entity-level LLD derived from HLD Section 6.
- `04-lld-services/`: service responsibilities, inputs, outputs, and extension points.
- `05-sdlc-and-delivery/`: implementation lifecycle, test evidence, and release readiness.

Recommended first read for Python/FastAPI developers:

- `00-onboarding/python-fastapi-to-rust-orientation.md`
- `04-lld-services/rust-codebase-skeleton.md`

## HLD to LLD Traceability

All docs in this folder must map to HLD sections and remain synchronized.
Any major implementation change must update the relevant LLD file(s) in the same change set.
