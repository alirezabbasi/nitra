# DEV-00015: Chart Interaction UX Parity Upgrade (15 Features)

## Status

Implemented

## Summary

Upgrade `charting` interaction UX to add commercial-grade exploration controls focused on chart behavior (not drawing panes/tools).

## Scope (15 Implemented Features)

1. Realtime recovery control (`Back to Realtime`).
2. Jump to timestamp navigation.
3. Jump to data-index navigation.
4. Zoom anchor control (`cursor` vs `last_bar`).
5. Candle density control (`setBarSpace`).
6. Right-side breathing room control (`setOffsetRightDistance`).
7. Left boundary minimum visible bars (`setLeftMinVisibleBarCount`).
8. Right boundary minimum visible bars (`setRightMinVisibleBarCount`).
9. Scroll lock toggle (`setScrollEnabled`).
10. Zoom lock toggle (`setZoomEnabled`).
11. Historical lazy-load while exploring left edge (`/api/v1/bars/history`).
12. Continuous live updates while preserving exploration mode.
13. Crosshair/visible-range driven UI metadata (`subscribeAction`).
14. Coordinate/value inspection via pixel/value conversion (`convertFromPixel`).
15. Snapshot export, locale/timezone controls, and number-format mode polish.

## Deliverables

- Frontend chart UX updates in `services/charting/static/index.html`.
- Backend historical pagination endpoint in `services/charting/app.py`.
- LLD and environment/contract docs updates.
- Test pack `tests/dev-0015/run.sh` and Make target.

## Acceptance Criteria

- Users can explore deep history without losing live feed continuity.
- Users can explicitly return to latest candle at any time.
- Users can control zoom, scroll, axis spacing, candle density, and chart margins.
- Users can jump directly to date/index and export chart snapshots.
- Range/crosshair metadata is visible and updates during interaction.
- Chart endpoint supports older-range pagination for lazy loading.
