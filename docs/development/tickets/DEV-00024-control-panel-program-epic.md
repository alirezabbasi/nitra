# DEV-00024: Control Panel Program Epic (Professional Admin Console)

## Status

Done (2026-04-29)

## Summary

Establish a full-featured, professional control panel for NITRA where all core capabilities are configurable and monitorable from a unified admin interface, with charting integrated as a sub-module.

## Product Direction

- UI stack: `shadcn/ui` components and patterns (`https://ui.shadcn.com/docs/components`).
- Visual language: professional black-and-white theme, high contrast, dense information layout, enterprise-grade consistency.
- Information architecture: persistent left sidebar with clear domain sections, role-aware navigation, and deep-linkable module routes.
- Operating model: configuration + observability + actionability in one surface (not a read-only dashboard).

## Core Objectives

- Single-pane operations for ingestion, structure, risk, portfolio, execution, research, and governance.
- Strong operator workflow support: triage, drilldown, replay, remediation, and auditability.
- Role-based control with explicit safeguards for high-risk actions.
- Charting embedded as a panel module with direct instrument-to-chart transitions.

## Scope Boundaries

- This epic defines the control panel program and decomposes implementation into topic-based tickets.
- Backend APIs can be incrementally added/extended where UI requirements expose gaps.
- No weakening of deterministic-core safety boundaries.

## Decomposed Tickets

1. `DEV-00025` foundation, shell, and design system.
2. `DEV-00026` authentication/RBAC and operator identity controls.
3. `DEV-00027` market ingestion and data-quality operations center.
4. `DEV-00028` strategy/risk/portfolio control center.
5. `DEV-00029` execution OMS and broker operations center.
6. `DEV-00030` charting workbench integration module.
7. `DEV-00031` alerting/incidents/runbooks center.
8. `DEV-00032` research/backtesting/model-ops center.
9. `DEV-00033` config registry, change control, and governance.
10. `DEV-00034` performance hardening, accessibility, and enterprise polish.

## Acceptance Criteria

- Ticket map is approved and implementation-ready.
- Each child ticket has clear scope, deliverables, non-goals, and verification.
- Kanban and active focus reference the control-panel program explicitly.

## Delivery Evidence Map

- `DEV-00025` done: shell/design-system baseline.
- `DEV-00026` done: auth/RBAC/operator identity.
- `DEV-00027` done: ingestion/data-quality operations center.
- `DEV-00028` done: strategy/risk/portfolio center.
- `DEV-00029` done: execution OMS/broker ops center.
- `DEV-00030` done: charting workbench integration.
- `DEV-00031` done: alerting/incidents/runbooks center.
- `DEV-00032` done: research/backtesting/model-ops center.
- `DEV-00033` done: config registry/change-control/governance center.
- `DEV-00034` done: enterprise polish/performance/accessibility.

Program-level outcome:
- Unified control panel now covers all major operational and governance modules with RBAC, auditability, and chart-integrated workflow continuity.

## Verification

- Documentation-only epic closure; no runtime code changes in this ticket.
- Child-ticket verification packs completed (`tests/dev-00025` .. `tests/dev-00034`).
