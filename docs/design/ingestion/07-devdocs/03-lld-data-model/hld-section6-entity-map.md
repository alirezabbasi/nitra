# HLD Section 6 Entity Map

Source of truth: HLD Section 6 in `docs/design/nitra_system_hld.md` and strategic baseline in `docs/design/AI-enabled_trading_decision_platform.md`.

## Current Coverage Snapshot

Implemented or partially implemented:

- `ohlcv_bar` -> `ohlcv_bar`
- `raw_tick` -> `raw_tick`
- `book_event` -> `book_event`
- `trade_print` -> `trade_print`
- `order_intent` -> represented via execution order events/topics
- `broker_order` -> `orders_recent`
- `execution_fill` -> `fills_recent`
- `risk_state` (partial) -> `risk_decisions`

Not yet fully implemented as first-class storage entities:

- `instrument`
- `session_calendar`
- `feature_snapshot`
- `signal_score`
- `regime_state`
- `portfolio_position`
- `trade_decision`
- `trade_outcome`
- `research_run`
- `model_version`
- `prompt_version`
- `retrieved_context`
- `audit_event`

## Required Direction

- Promote missing entities into explicit schema objects.
- Define keys, timestamps, idempotency, and retention for each entity.
- Keep hot/cold/lakehouse representations consistent and auditable.
