# DEV-0024: Control Panel Program Epic (Professional Admin Console)

## Status

Open

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

1. `DEV-0025` foundation, shell, and design system.
2. `DEV-0026` authentication/RBAC and operator identity controls.
3. `DEV-0027` market ingestion and data-quality operations center.
4. `DEV-0028` strategy/risk/portfolio control center.
5. `DEV-0029` execution OMS and broker operations center.
6. `DEV-0030` charting workbench integration module.
7. `DEV-0031` alerting/incidents/runbooks center.
8. `DEV-0032` research/backtesting/model-ops center.
9. `DEV-0033` config registry, change control, and governance.
10. `DEV-0034` performance hardening, accessibility, and enterprise polish.

## Acceptance Criteria

- Ticket map is approved and implementation-ready.
- Each child ticket has clear scope, deliverables, non-goals, and verification.
- Kanban and active focus reference the control-panel program explicitly.

## Verification

- Documentation-only epic setup; no runtime changes in this ticket.
