# 06 — State Machines

## 1. Pullback State Machine

### States
- `NONE`
- `ACTIVE`
- `EXTENDED`
- `TERMINATED`

### Inputs
- current candle
- active reference candle
- directional bias
- inside/outside bar classification
- structural archive

### Bearish Example Logic
- `NONE -> ACTIVE` when `B.high > A.high` and `A.low` not broken
- `ACTIVE -> EXTENDED` when subsequent candles continue breaking previous highs while active termination low remains intact
- `ACTIVE|EXTENDED -> TERMINATED` when termination reference low is broken by wick or body

### Reference Management
- inside bar normally ignored
- inside bar with equal-low to reference shifts active reference to inside bar
- outside bar starts pullback
- if outside bar is extended by next candle, termination reference shifts to outside bar low
- otherwise termination reference remains prior reference low

---

## 2. Minor Structure Confirmation State Machine

### States
- `WAITING_FOR_PULLBACK`
- `PULLBACK_IN_PROGRESS`
- `MINOR_PAIR_PENDING`
- `MINOR_PAIR_CONFIRMED`

### Transition Logic
1. detect pullback start
2. track highest high during pullback
3. on pullback termination:
   - confirm `minor_low`
   - confirm `minor_high`
   - append pair to archive
4. set newest pair as active

---

## 3. Major Structure Activation State Machine

### States
- `NO_MAJOR_EVENT`
- `CANDIDATE_MAJOR_BREAK`
- `MAJOR_CONFIRMED`

### Transition Logic
- move to `CANDIDATE_MAJOR_BREAK` when pullback high exceeds any archived structural high
- confirm `major_high` as highest price reached by the breaking pullback before termination
- confirm `major_low` as the lowest price immediately before that pullback began
- persist major pair on pullback termination

---

## 4. Risk Decision State Machine

### States
- `RECEIVED`
- `VALIDATING`
- `APPROVED`
- `REJECTED`
- `EXPIRED`

### Checks
- account active
- strategy enabled
- venue tradable
- symbol whitelist / blacklist
- net exposure limit
- per-trade notional limit
- portfolio drawdown limit
- duplicate intent guard
- kill switch status

---

## 5. Order State Machine

### States
- `CREATED`
- `VALIDATED`
- `SUBMITTED`
- `ACKNOWLEDGED`
- `PARTIALLY_FILLED`
- `FILLED`
- `CANCEL_PENDING`
- `CANCELED`
- `REJECTED`
- `EXPIRED`
- `RECONCILIATION_ERROR`

### Transitions
- `CREATED -> VALIDATED` after local schema + risk linkage validation
- `VALIDATED -> SUBMITTED` after broker API acceptance attempt
- `SUBMITTED -> ACKNOWLEDGED` on broker ack
- `ACKNOWLEDGED -> PARTIALLY_FILLED` on first partial fill
- `ACKNOWLEDGED|PARTIALLY_FILLED -> FILLED` when remaining qty == 0
- `ACKNOWLEDGED|PARTIALLY_FILLED -> CANCEL_PENDING` on cancel request
- `CANCEL_PENDING -> CANCELED` on broker confirm
- `SUBMITTED|ACKNOWLEDGED -> REJECTED` on broker reject
- any active state -> `RECONCILIATION_ERROR` if broker/internal state diverges beyond tolerance

### Timers
- submit timeout
- ack timeout
- fill timeout
- reconciliation timeout

---

## 6. AI Analysis Acceptance State Machine

### States
- `REQUESTED`
- `RETRIEVING`
- `GENERATED`
- `VALIDATED`
- `ACCEPTED`
- `REJECTED`

### Rejection Triggers
- invalid JSON/schema
- missing cited state references
- contradiction with deterministic structure snapshot
- forbidden action content
- confidence below threshold
