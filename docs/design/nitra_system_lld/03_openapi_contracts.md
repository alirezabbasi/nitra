# 03 — OpenAPI Contracts (LLD Draft)

## 1. Structure Snapshot API

### `GET /v1/structure/{symbol}/current`
Returns the latest deterministic structure state.

```yaml
get:
  summary: Get current structure state
  parameters:
    - in: path
      name: symbol
      required: true
      schema: { type: string }
  responses:
    '200':
      description: Current structure snapshot
      content:
        application/json:
          schema:
            type: object
            required:
              - symbol
              - timeframe
              - directional_bias
              - active_reference
              - pullback_state
              - archive_version
              - created_at
            properties:
              symbol: { type: string }
              timeframe: { type: string, enum: [1s, 1m, 5m, 15m, 1h] }
              directional_bias: { type: string, enum: [bullish, bearish, neutral] }
              liquidity_objective:
                type: object
                properties:
                  side: { type: string, enum: [upper, lower, none] }
                  target_price: { type: number }
              active_reference:
                type: object
                properties:
                  candle_id: { type: string }
                  high: { type: number }
                  low: { type: number }
              pullback_state:
                type: string
                enum: [none, active, extended, terminated]
              minor_active:
                type: object
                nullable: true
                properties:
                  minor_low: { type: number }
                  minor_high: { type: number }
              major_active:
                type: object
                nullable: true
                properties:
                  major_low: { type: number }
                  major_high: { type: number }
              archive_version: { type: integer }
              created_at: { type: string, format: date-time }
```

---

## 2. Feature API

### `POST /v1/features/online`
Returns point-in-time online features for inference.

```yaml
post:
  summary: Get online features
  requestBody:
    required: true
    content:
      application/json:
        schema:
          type: object
          required: [entity_key, as_of, feature_view_names]
          properties:
            entity_key:
              type: object
              additionalProperties: true
            as_of:
              type: string
              format: date-time
            feature_view_names:
              type: array
              items: { type: string }
  responses:
    '200':
      description: Online features
```

---

## 3. Signal Scoring API

### `POST /v1/inference/score`
Scores a candidate using registered production models.

```yaml
post:
  summary: Score candidate
  requestBody:
    required: true
    content:
      application/json:
        schema:
          type: object
          required:
            - symbol
            - timeframe
            - structure_snapshot_id
            - feature_snapshot
          properties:
            symbol: { type: string }
            timeframe: { type: string }
            structure_snapshot_id: { type: string }
            feature_snapshot:
              type: object
              additionalProperties: true
  responses:
    '200':
      description: Scored result
      content:
        application/json:
          schema:
            type: object
            required: [signal_score, confidence, model_name, model_version]
            properties:
              signal_score: { type: number }
              confidence: { type: number }
              regime: { type: string }
              anomaly_flags:
                type: array
                items: { type: string }
              model_name: { type: string }
              model_version: { type: string }
```

---

## 4. Risk Check API

### `POST /v1/risk/check`
Validates whether a candidate order is tradable.

```yaml
post:
  summary: Run pre-trade risk checks
  requestBody:
    required: true
    content:
      application/json:
        schema:
          type: object
          required:
            - symbol
            - side
            - proposed_qty
            - proposed_price
            - strategy_id
            - signal_score
          properties:
            symbol: { type: string }
            side: { type: string, enum: [buy, sell] }
            proposed_qty: { type: number }
            proposed_price: { type: number }
            strategy_id: { type: string }
            signal_score: { type: number }
  responses:
    '200':
      description: Risk decision
      content:
        application/json:
          schema:
            type: object
            required: [approved, decision_id]
            properties:
              approved: { type: boolean }
              decision_id: { type: string }
              rejection_reasons:
                type: array
                items: { type: string }
              max_allowed_qty: { type: number }
```

---

## 5. Order Intent API

### `POST /v1/execution/intents`
Creates an execution intent from an approved risk decision.

```yaml
post:
  summary: Submit execution intent
  requestBody:
    required: true
    content:
      application/json:
        schema:
          type: object
          required:
            - risk_decision_id
            - symbol
            - side
            - qty
            - order_type
          properties:
            risk_decision_id: { type: string }
            symbol: { type: string }
            side: { type: string, enum: [buy, sell] }
            qty: { type: number }
            order_type: { type: string, enum: [market, limit, stop, stop_limit] }
            limit_price: { type: number, nullable: true }
            tif: { type: string, enum: [day, gtc, ioc, fok] }
  responses:
    '202':
      description: Intent accepted
```

---

## 6. LLM Analysis API

### `POST /v1/analysis/structure`
Returns schema-constrained AI analysis over deterministic state.

```yaml
post:
  summary: Analyze structure snapshot
  requestBody:
    required: true
    content:
      application/json:
        schema:
          type: object
          required:
            - structure_snapshot_id
            - retrieval_scope
          properties:
            structure_snapshot_id: { type: string }
            retrieval_scope:
              type: array
              items: { type: string }
  responses:
    '200':
      description: Structured AI analysis
      content:
        application/json:
          schema:
            type: object
            required:
              - framework_alignment
              - interpretation
              - ambiguities
              - confidence
            properties:
              framework_alignment: { type: string, enum: [aligned, partial, failed] }
              interpretation:
                type: object
                additionalProperties: true
              ambiguities:
                type: array
                items: { type: string }
              confidence: { type: number }
```

## Contract Rules
- every endpoint versioned under `/v1`
- all request/response bodies validated
- all write APIs idempotency-key capable
- all mutating APIs emit audit records
- request tracing header required: `x-trace-id`
