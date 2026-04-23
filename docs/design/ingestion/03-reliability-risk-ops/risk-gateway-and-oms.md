# Risk Gateway and OMS Controls

## Objective

EPIC-09 enforces non-bypassable pre-trade risk decisions and deterministic OMS lifecycle handling.

## Risk Gateway (`services/risk_gateway`)

Input:
- Topic: `execution.orders`
- Payload: `Envelope<ExecutionOrderEvent::Intent>`

Output:
- Topic: `risk.events`
- Payload: `Envelope<RiskDecisionEvent>`

Controls:
1. Kill switch (`RISK_KILL_SWITCH`).
2. Per-order quantity cap (`RISK_MAX_ORDER_QTY`).
3. Per-order notional cap (`RISK_MAX_ORDER_NOTIONAL`).
4. Daily post-trade notional cap from `fills_recent` (`RISK_MAX_DAILY_FILLED_NOTIONAL`).

Persistence:
- Every evaluated command is stored in `risk_decisions`.
- Idempotency is enforced with unique `command_id`.

Non-bypass guarantee:
- OMS consumes only `risk.events` decisions for submission.
- No direct order submission path exists in OMS without a prior risk decision.

## OMS (`services/oms`)

Inputs:
- `risk.events` (`RiskDecisionEvent`)
- `execution.fills` (`FillEvent`)

Outputs:
- `execution.orders` (`ExecutionOrderEvent::State`)

State machine:
1. `submitted`
2. `partially_filled`
3. `filled`
4. `rejected`
5. `reconcile_hold`

Persistence:
- Orders: `orders_recent` (unique `command_id`, optional unique `broker_order_id`)
- Fills: `fills_recent` (unique `venue_fill_id` for idempotent fill handling)
- Reconciliation findings: `oms_reconciliation_log`

Reconciliation policy:
- Detect stale open orders and overfills.
- Apply `flag_and_hold` policy.
- Write audit record and move order to `reconcile_hold`.

## Operational Notes

- Risk persistence table is in `infra/timescaledb/init/005_risk_controls.sql`.
- OMS lifecycle and reconciliation tables are in `infra/timescaledb/init/006_oms_lifecycle.sql`.
- Data durability follows project rule: no destructive cleanup commands are used in runtime flows.
