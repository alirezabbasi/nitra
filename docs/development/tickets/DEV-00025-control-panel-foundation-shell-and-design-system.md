# DEV-00025: Control Panel Foundation, Shell, and Design System

## Status

Done (2026-04-28)

## Summary

Build the control panel app shell, route framework, role-aware sidebar navigation, and black-and-white shadcn-based design foundation.

## Scope

- Bootstrap admin frontend module under `services/charting` app boundary or dedicated admin app path.
- Implement app shell:
  - persistent left sidebar
  - top command strip
  - workspace content area
- Define route groups for all major domains.
- Introduce shadcn component baseline and styling tokens for black-and-white enterprise theme.
- Add layout primitives for tables, filters, split panes, and detail drawers.

## Non-Goals

- Deep domain logic for risk/execution/portfolio workflows.
- Advanced analytics visualizations beyond shell placeholders.

## Acceptance Criteria

- Sidebar and route skeleton for all planned modules exists.
- Theme tokens and component variants are consistent and reusable.
- UX is responsive and production-grade on desktop and laptop widths.

## Verification

- UI smoke route tests.
- Visual consistency checks for core templates.
- `tests/dev-00025/run.sh`
