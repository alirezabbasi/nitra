# Ingestion Service Environment Variables (DEV-00005)

This page defines environment variables for the minimal ingestion runtime wired in NITRA compose.

## persistence paths (compose bind mounts)

- `TIMESCALEDB_DATA_PATH` default `./.runtime-data/timescaledb`
- `REDIS_DATA_PATH` default `./.runtime-data/redis`
- `KAFKA_DATA_PATH` default `./.runtime-data/kafka`
- `MINIO_DATA_PATH` default `./.runtime-data/minio`

Operational notes:
- Stateful services use bind mounts under `.runtime-data/` by default.
- `docker compose down -v` removes named volumes, but bind-mounted runtime data remains unless those directories are manually deleted.

## charting

- `CHARTING_PORT` default `8110`
- `CHARTING_TIMEFRAME` default `1m`
- `CHARTING_DEFAULT_LIMIT` default `300`
- `CHARTING_REFRESH_SECS` default `5`
- `OANDA_API_TOKEN` optional; required for strict venue-history backfill on OANDA symbols
- `OANDA_REST_URL` default `https://api-fxpractice.oanda.com`
- `COINBASE_REST_URL` default `https://api.exchange.coinbase.com`
- `COINBASE_PUBLIC_REST_URL` default `https://api.coinbase.com` (fallback public candles route)
- `CAPITAL_API_URL` (required for Capital history adapter)
- `CAPITAL_API_KEY` (required for Capital history adapter)
- `CAPITAL_IDENTIFIER` (required for Capital history adapter)
- `CAPITAL_API_PASSWORD` (required for Capital history adapter)
- `CAPITAL_EPIC_MAP` optional JSON map for canonical symbol -> epic (for example `{"EURUSD":"CS.D.EURUSD.MINI.IP"}`)
- `CHARTING_VENUE_FETCH_TIMEOUT_SECS` default `8` (per-request timeout for venue history backfill calls)
- `CHARTING_VENUE_FETCH_MAX_ERRORS` default `3` (fail-fast threshold before aborting long backfill loops)

Operational notes:
- Backfill range priority is newest-to-oldest so recent continuity is restored first.
- 90-day historical coverage ownership is in ingestion services (`gap-detection`, `backfill-worker`, `replay-controller`), not in charting.
- Charting may expose trigger/observability endpoints, but ingestion coverage/backfill must continue even if charting is unavailable.
- New APIs:
  - `POST /api/v1/backfill/window` for explicit `from_ts`/`to_ts` backfill windows.
  - `GET /api/v1/coverage/status` for symbol-level 90d coverage and gap/backfill status.
  - `GET /api/v1/coverage/metrics` for dashboard/Prometheus-style summary gauges.
- For non-`1m` chart timeframes, charting API derives candles from `1m` storage, so once `1m` backfill is complete, higher timeframes become available without waiting for native timeframe persistence.

## market-ingestion services (parallel)

The compose runtime starts three ingestion services simultaneously:

- `market-ingestion-oanda` (OANDA)
- `market-ingestion-capital` (CAPITAL)
- `market-ingestion-coinbase` (COINBASE)

Shared:

- `KAFKA_BROKERS` default `kafka:9092`
- `INGESTION_HEALTH_TOPIC` default `connector.health`
- `DATABASE_URL` required for DB-backed venue/market config reads
- `INGESTION_SYMBOL_SOURCE` default `database` (`database` = load active symbols from `venue_market`; `env` = use `*_ENABLED_INSTRUMENTS`)
- `INGESTION_DB_REFRESH_SECS` default `30` (reload cadence for active market config)
- `INGESTION_RATE_LIMIT_POLICY_ENABLED` default `true`
- `INGESTION_RATE_LIMIT_POLICY_REFRESH_SECS` default `30` (reload cadence for DB-backed per-venue throttling contract)
- `INGESTION_RATE_LIMIT_MIN_POLL_MS` default derived from venue poll interval (lower bound)
- `INGESTION_RATE_LIMIT_MAX_POLL_MS` default `8000` (upper bound)
- `INGESTION_RATE_LIMIT_BACKOFF_MULTIPLIER` default `1.6`
- `INGESTION_RATE_LIMIT_RECOVERY_STEP_MS` default `100`
- `INGESTION_RATE_LIMIT_BURST_COOLDOWN_SECONDS` default `30`
- `INGESTION_RATE_LIMIT_MAX_CONSECUTIVE_HITS` default `3`
- `INGESTION_RATE_LIMIT_SOFT_LIMIT_PER_MINUTE` default `120`
- `FX_WEEKEND_START_ISO_DOW` default `6` (Saturday)
- `FX_WEEKEND_START_HOUR_UTC` default `0`
- `FX_WEEKEND_END_ISO_DOW` default `1` (Monday)
- `FX_WEEKEND_END_HOUR_UTC` default `6`

OANDA profile:

- `OANDA_RAW_TOPIC` default `raw.market.oanda`
- `OANDA_DEFAULT_INSTRUMENT` default `EURUSD`
- `OANDA_ENABLED_INSTRUMENTS` default `EURUSD,GBPUSD,USDJPY`
- `OANDA_POLL_INTERVAL_SECS` default `1.0`
- `OANDA_STREAM_URL`
- `OANDA_REST_URL` default `https://api-fxpractice.oanda.com` (used for pricing REST fallback/normalization of stream host)
- `OANDA_ACCOUNT_ID`
- `OANDA_API_TOKEN`
- `OANDA_INSTRUMENT_MAP` optional JSON map for canonical symbol -> OANDA instrument
  (for example `{"NAS100":"NAS100_USD","US30":"US30_USD","XAUUSD":"XAU_USD"}`)

CAPITAL profile:

- `CAPITAL_RAW_TOPIC` default `raw.market.capital`
- `CAPITAL_DEFAULT_INSTRUMENT` default `EURUSD`
- `CAPITAL_ENABLED_INSTRUMENTS` default `EURUSD,GBPUSD`
- `CAPITAL_POLL_INTERVAL_SECS` default `1.0`
- `CAPITAL_API_URL`
- `CAPITAL_API_KEY`
- `CAPITAL_IDENTIFIER`
- `CAPITAL_API_PASSWORD`
- `CAPITAL_EPIC_ALLOWLIST`
- `CAPITAL_EPIC_MAP` optional JSON map for canonical symbol -> venue epic (for example `{"EURUSD":"CS.D.EURUSD.MINI.IP"}`)

Note:

- Pair symbols are emitted in compact alphanumeric format only (for example `EURUSD`, `GBPUSD`, `BTCUSD`) with no `_`, `-`, or dot separators.
- Synthetic/mock quote generation is prohibited in runtime ingestion services.
- `CONNECTOR_MODE=mock` is explicitly rejected by `market-ingestion` (fail-closed startup behavior).
- FX venues (`oanda`, `capital`) pause symbol fetches during configured weekend close window; Coinbase remains active (`24/7`).
- Gap-detection coverage scan also honors FX weekend session policy (`FX_WEEKEND_*`) so startup/periodic 90-day conformance excludes expected closed buckets for FX while preserving `24/7` crypto expectations.
- Active market list source of truth for ingestion runtime control is DB table `venue_market`.

COINBASE profile:

- `COINBASE_RAW_TOPIC` default `raw.market.coinbase`
- `COINBASE_DEFAULT_INSTRUMENT` default `BTCUSD`
- `COINBASE_ENABLED_INSTRUMENTS` default `BTCUSD,ETHUSD,SOLUSD,ADAUSD,XRPUSD`
- `COINBASE_POLL_INTERVAL_SECS` default `1.0`
- `COINBASE_WS_URL`
- `COINBASE_REST_URL` default `https://api.exchange.coinbase.com`
- `COINBASE_PUBLIC_REST_URL` default `https://api.coinbase.com` (spot-price fallback when Exchange ticker endpoint is unavailable per product/runtime)
- `COINBASE_PRODUCT_ALLOWLIST`
- `COINBASE_CHANNELS`

## market-normalization

- `KAFKA_BROKERS` default `kafka:9092`
- `NORMALIZER_INPUT_TOPICS` default `raw.market.oanda,raw.market.capital,raw.market.coinbase`
- `NORMALIZER_OUTPUT_TOPIC` default `normalized.quote.fx`
- `NORMALIZER_GROUP_ID` default `nitra-market-normalization-v1`
- `NORMALIZER_SYMBOL_REGISTRY_PATH` default `/app/ingestion/registry.v1.json`
- `DATABASE_URL` required (compose sets from `POSTGRES_*`)
- Re-ingest resolution header contract:
  - `headers.quarantine_reingest=true` marks matching quarantined source event as `reingested` after successful deterministic processing.

## bar-aggregation

- `KAFKA_BROKERS` default `kafka:9092`
- `BAR_INPUT_TOPIC` default `normalized.quote.fx`
- `BAR_OUTPUT_TOPIC` default `bar.10s`
- `BAR_GROUP_ID` default `nitra-bar-aggregation-v1`
- `DATABASE_URL` required (compose sets from `POSTGRES_*`)

## gap-detection

- `KAFKA_BROKERS` default `kafka:9092`
- `GAP_INPUT_TOPIC` default `bar.10s`
- `GAP_OUTPUT_TOPIC` default `gap.events`
- `GAP_GROUP_ID` default `nitra-gap-detection-v1`
- `GAP_STARTUP_SCAN_ENABLED` default `true`
- `GAP_STARTUP_COVERAGE_DAYS` default `90` (runtime-enforced minimum is `90`)
- `GAP_ACTIVE_MARKET_DB_LOOKBACK_HOURS` default `24`
- `GAP_PERIODIC_SCAN_ENABLED` default `true` (continuous 90d coverage scanner)
- `GAP_PERIODIC_SCAN_INTERVAL_SECS` default `300` (periodic scan interval)
- `GAP_PERIODIC_SCAN_MARKETS_PER_CYCLE` default `64` (bounded market scan per cycle)
- `GAP_SYMBOL_REGISTRY_PATH` default `/etc/nitra/registry.v1.json`
- `GAP_INCLUDE_DB_DISCOVERED_MARKETS` default `false` (when `false`, gap scanner is registry-scoped only to avoid accidental market fanout)
- `DATABASE_URL` required (compose sets from `POSTGRES_*`)

## backfill-worker

- `KAFKA_BROKERS` default `kafka:9092`
- `BACKFILL_INPUT_TOPIC` default `gap.events`
- `BACKFILL_REPLAY_TOPIC` default `replay.commands`
- `BACKFILL_GROUP_ID` default `nitra-backfill-worker-v1`
- `BACKFILL_TARGET_GROUP` default `nitra-market-normalization-v1`
- `BACKFILL_SYMBOL_REGISTRY_PATH` default `/etc/nitra/registry.v1.json`
- `BACKFILL_STARTUP_PROCESS_OPEN_GAPS` default `true`
- `BACKFILL_FETCH_CHUNK_MINUTES` default `1440` (larger default to reduce queue pressure for 90d rebuilds)
- `BACKFILL_RECOVERY_ENABLED` default `true` (periodically re-enqueue orphaned `queued` jobs into `replay.commands`)
- `BACKFILL_RECOVERY_INTERVAL_SECS` default `30`
- `BACKFILL_RECOVERY_BATCH_SIZE` default `1500`
- `BACKFILL_STALE_RUNNING_SECS` default `600` (auto-reset stale `running` jobs back to `queued`)
- `BACKFILL_QUEUED_STALE_SECS` default `900` (queued job must be stale before recovery re-enqueue is allowed)
- `BACKFILL_REENQUEUE_COOLDOWN_SECS` default `90` (minimum interval between re-enqueue attempts for same job)
- `BACKFILL_FAILED_RETRY_ENABLED` default `true` (allow controlled retries for `failed_no_source_data` jobs)
- `BACKFILL_FAILED_RETRY_AFTER_SECS` default `21600` (cooldown before retry-eligible `failed_no_source_data` jobs are re-queued)
- `BACKFILL_FAILED_RETRY_MAX_ATTEMPTS` default `6` (cap failed-range retry attempts)
- `BACKFILL_FAILED_RETRY_BATCH_SIZE` default `300` (per-cycle cap for failed-range requeue)
- `BACKFILL_REPLAY_QUEUE_BACKPRESSURE_ENABLED` default `true` (watermark-based pressure control for queued replay backlog)
- `BACKFILL_REPLAY_QUEUE_HIGH_WATERMARK` default `120000` (hard-stop re-enqueue above this queued replay count)
- `BACKFILL_REPLAY_QUEUE_LOW_WATERMARK` default `90000` (full recovery batch allowed below this queued replay count)
- `BACKFILL_REPLAY_QUEUE_MIN_BATCH` default `100` (minimum dynamic batch while queue sits between low/high watermarks)
- `DATABASE_URL` required (compose sets from `POSTGRES_*`)

## replay-controller

- `KAFKA_BROKERS` default `kafka:9092`
- `REPLAY_INPUT_TOPIC` default `replay.commands`
- `REPLAY_GROUP_ID` default `nitra-replay-controller-v1`
- `REPLAY_WORKER_COUNT` default `8` (parallel Kafka consumers in one process, same consumer-group for safe partition-level scaling)
- `REPLAY_SYMBOL_REGISTRY_PATH` default `/etc/nitra/registry.v1.json`
- `REPLAY_HISTORY_ENABLED` default `true` (attempt venue-history adapter fetch when raw ticks are insufficient for replay range)
- `REPLAY_HISTORY_TIMEOUT_SECS` default `8` (HTTP timeout for venue-history requests)
- `REPLAY_OANDA_REST_URL` default `${OANDA_REST_URL}`
- `REPLAY_OANDA_API_TOKEN` default `${OANDA_API_TOKEN}` (required for OANDA history adapter)
- `REPLAY_OANDA_INSTRUMENT_MAP` default `${REPLAY_OANDA_INSTRUMENT_MAP}` (optional canonical symbol -> OANDA instrument override map)
- `REPLAY_COINBASE_REST_URL` default `${COINBASE_REST_URL}`
- `REPLAY_COINBASE_PUBLIC_REST_URL` default `${COINBASE_PUBLIC_REST_URL}` (fallback candles route when Exchange endpoint is blocked)
- `REPLAY_COINBASE_USER_AGENT` default `nitra-replay-controller/1.0` (required by some Coinbase Exchange runtimes)
- `REPLAY_CAPITAL_API_URL` default `${CAPITAL_API_URL}`
- `REPLAY_CAPITAL_API_KEY` default `${CAPITAL_API_KEY}`
- `REPLAY_CAPITAL_IDENTIFIER` default `${CAPITAL_IDENTIFIER}`
- `REPLAY_CAPITAL_API_PASSWORD` default `${CAPITAL_API_PASSWORD}`
- `REPLAY_CAPITAL_EPIC_MAP` default `${CAPITAL_EPIC_MAP}` (optional canonical symbol -> epic map)
- `DATABASE_URL` required (compose sets from `POSTGRES_*`)

Notes:
- Replay executor first rebuilds `1m` bars from `raw_tick`; if the range remains incomplete, it attempts venue-history adapters (`oanda`/`coinbase`/`capital`) before finalizing status.
- Venue-history fetch in replay is window-paginated for long ranges (backend-only 90d recovery without chart trigger dependency).
- Backfill recovery loop is persistent: stale `running` rows auto-reset, and `queued` jobs are periodically re-enqueued for replay execution so recovery can continue after consumer interruptions.
- Recovery re-enqueue is stale-only: jobs are replayed only when queue/audit timestamps indicate they are stuck, and selection order is oldest pending enqueue first.
- Recovery applies replay-queue backpressure: re-enqueue batch is dynamically reduced between low/high queued watermarks and hard-stopped above high watermark to prevent unbounded queue growth.
- Registry guardrails are fail-closed: unknown `(venue, canonical_symbol)` pairs are ignored in backfill and marked failed in replay to prevent infinite queue churn from bad mappings.

## structure-engine

- `KAFKA_BROKERS` default `kafka:9092`
- `STRUCTURE_INPUT_TOPIC` default `bar.10s`
- `STRUCTURE_SNAPSHOT_TOPIC` default `structure.snapshot.v1`
- `STRUCTURE_PULLBACK_TOPIC` default `structure.pullback.v1`
- `STRUCTURE_MINOR_TOPIC` default `structure.minor_confirmed.v1`
- `STRUCTURE_MAJOR_TOPIC` default `structure.major_confirmed.v1`
- `STRUCTURE_GROUP_ID` default `nitra-structure-engine-v1`
- `DATABASE_URL` required (compose sets from `POSTGRES_*`)

Notes:
- The baseline runtime is deterministic and replay-safe (`processed_message_ledger` idempotency).
- Structure state is persisted in `structure_state` (single source of truth per `venue + symbol + timeframe`).
- Baseline transitions emit snapshots on every bar and emit pullback/minor/major confirmations from deterministic state transitions.

## feature-service

- `KAFKA_BROKERS` default `kafka:9092`
- `FEATURE_INPUT_TOPIC` default `structure.snapshot.v1`
- `FEATURE_OUTPUT_TOPIC` default `features.snapshot.v1`
- `FEATURE_GROUP_ID` default `nitra-feature-service-v1`
- `FEATURE_SET_VERSION` default `dev-00038.v1`
- `DATABASE_URL` required (compose sets from `POSTGRES_*`)

Notes:
- Baseline `DEV-00038` implementation computes deterministic PIT-safe feature vectors from structure snapshots.
- No-lookahead contract: only current snapshot payload + previously persisted state may be used.
- Feature lineage contract persists source topic/partition/offset and window metadata in `feature_snapshot.lineage`.
- Output contract topic: `features.snapshot.v1`.

## signal-engine (inference-gateway baseline)

- `KAFKA_BROKERS` default `kafka:9092`
- `SIGNAL_INPUT_TOPIC` default `features.snapshot.v1`
- `SIGNAL_OUTPUT_TOPIC` default `decision.signal_scored.v1`
- `SIGNAL_GROUP_ID` default `nitra-signal-engine-v1`
- `SIGNAL_SCORER_CONFIG_VERSION` default `dev-00039.v1`
- `SIGNAL_MODEL_VERSION` default `deterministic-linear-v1`
- `SIGNAL_SCORE_THRESHOLD_BUY` default `0.62`
- `SIGNAL_SCORE_THRESHOLD_SELL` default `-0.62`
- `SIGNAL_CONFIDENCE_CAP` default `0.99`
- `DATABASE_URL` required (compose sets from `POSTGRES_*`)

Notes:
- `DEV-00039` baseline emits deterministic scored signal payloads on `decision.signal_scored.v1`.
- Explainability contract includes `reason_codes`, `feature_refs`, and pinned scorer/model versions.
- Calibration harness is implemented in-service (`run_calibration`) for reproducible distribution checks.

## risk-engine

- `KAFKA_BROKERS` default `kafka:9092`
- `RISK_INPUT_TOPIC` default `decision.signal_scored.v1`
- `RISK_CHECKED_TOPIC` default `decision.risk_checked.v1`
- `RISK_VIOLATION_TOPIC` default `ops.policy_violation.v1`
- `RISK_GROUP_ID` default `nitra-risk-engine-v1`
- `RISK_MIN_CONFIDENCE` default `0.55`
- `RISK_MAX_NOTIONAL` default `100000`
- `RISK_MAX_DRAWDOWN_PCT` default `5`
- `RISK_DEFAULT_NOTIONAL` default `1000`
- `RISK_MAX_SYMBOL_EXPOSURE_NOTIONAL` default `250000`
- `RISK_MAX_PORTFOLIO_GROSS_EXPOSURE_NOTIONAL` default `500000`
- `RISK_MIN_AVAILABLE_EQUITY` default `10000`
- `RISK_PORTFOLIO_ACCOUNT_ID` default `paper`
- `RISK_POLICY_BUNDLE_ID` default `risk-policy-bundle-dev-0040-v1`
- `RISK_MAX_REGIME_VOLATILITY` default `0.95`
- `RISK_MAX_CONFLICT_SCORE` default `0.9`
- `RISK_KILL_SWITCH_MODE` default `strict`
- `DATABASE_URL` required (compose sets from `POSTGRES_*`)

Notes:
- The baseline risk service is deterministic and fail-closed for kill-switch/drawdown/notional/confidence and portfolio-cap violations.
- Decision traceability baseline (`DEV-00040`) adds canonical policy-hit IDs and JSON evaluation traces on every decision event and in `risk_decision_log`.
- Risk state and audit history are persisted in `risk_state` and `risk_decision_log`.
- `processed_message_ledger` idempotency is enforced to keep replay-safe decision behavior.

## portfolio-engine

- `KAFKA_BROKERS` default `kafka:9092`
- `PORTFOLIO_INPUT_FILL_TOPIC` default `exec.fill_received.v1`
- `PORTFOLIO_SNAPSHOT_TOPIC` default `portfolio.snapshot.v1`
- `PORTFOLIO_GROUP_ID` default `nitra-portfolio-engine-v1`
- `PORTFOLIO_ACCOUNT_ID` default `paper`
- `PORTFOLIO_DEFAULT_EQUITY` default `100000`
- `PORTFOLIO_MAX_GROSS_EXPOSURE_NOTIONAL` default `1000000`
- `PORTFOLIO_MAX_ABS_NET_EXPOSURE_NOTIONAL` default `1000000`
- `PORTFOLIO_MIN_EQUITY` default `1000`
- `PORTFOLIO_DRIFT_TOPIC` default `exec.reconciliation_issue.v1`
- `DATABASE_URL` required (compose sets from `POSTGRES_*`)

Notes:
- Baseline portfolio runtime is deterministic and replay-safe via `processed_message_ledger`.
- Portfolio baseline persistence contracts: `portfolio_position_state`, `portfolio_account_state`, `portfolio_fill_log`.
- Baseline portfolio snapshots are emitted on `portfolio.snapshot.v1` for downstream controls and observability.
- Reconciliation hardening (`DEV-00042`) adds invariant checks and reconciliation evidence persistence in `portfolio_reconciliation_log`.
- Drift conditions emit deterministic reconciliation issues on `PORTFOLIO_DRIFT_TOPIC`.

## execution-gateway

- `KAFKA_BROKERS` default `kafka:9092`
- `EXECUTION_INPUT_TOPIC` default `decision.risk_checked.v1`
- `EXECUTION_COMMAND_TOPIC` default `exec.order_command.v1`
- `EXECUTION_BROKER_ACK_TOPIC` default `broker.execution.ack.v1`
- `EXEC_ORDER_SUBMITTED_TOPIC` default `exec.order_submitted.v1`
- `EXEC_ORDER_UPDATED_TOPIC` default `exec.order_updated.v1`
- `EXEC_FILL_RECEIVED_TOPIC` default `exec.fill_received.v1`
- `EXEC_RECONCILIATION_ISSUE_TOPIC` default `exec.reconciliation_issue.v1`
- `EXECUTION_GROUP_ID` default `nitra-execution-gateway-v1`
- `EXEC_DRY_RUN` default `true`
- `EXEC_ORDER_TTL_SECS` default `30`
- `EXEC_BROKER_SUBMIT_URL` default `http://broker-adapter:8080/orders/submit`
- `EXEC_BROKER_AMEND_URL` default `http://broker-adapter:8080/orders/amend`
- `EXEC_BROKER_CANCEL_URL` default `http://broker-adapter:8080/orders/cancel`
- `EXEC_BROKER_TIMEOUT_SECS` default `5`
- `EXEC_BROKER_RETRY_MAX_ATTEMPTS` default `3` (deterministic upper bound per adapter call)
- `EXEC_BROKER_RETRY_BACKOFF_MS` default `200` (base backoff in milliseconds)
- `EXEC_BROKER_RETRY_BACKOFF_CAP_MS` default `2000` (max exponential backoff cap in milliseconds)
- `EXEC_BROKER_DEGRADED_COOLDOWN_MS` default `250` (post-terminal-failure cooldown to avoid retry storms)
- `EXEC_COMMAND_STALE_AFTER_SECS` default `120` (reject command events that are too old relative to order update timeline)
- `EXEC_COMMAND_DUPLICATE_WINDOW_SECS` default `300` (deterministic duplicate command rejection window)
- `EXEC_RECONCILIATION_SLA_SECS` default `180` (SLA threshold for reconciliation-age breach context emission)
- `DATABASE_URL` required (compose sets from `POSTGRES_*`)

Notes:
- Baseline execution flow is deterministic and journaled (`execution_order_journal` + `audit_event_log` + `execution_command_log`).
- `processed_message_ledger` idempotency is enforced to avoid duplicate execution transitions under replay/restart.
- Broker adapter routing baseline supports submit/amend/cancel calls and broker ack/fill ingestion.
- Adapter failures are now classified and persisted (`dns_resolution`, `connect_timeout`, `io_timeout`, `upstream_5xx`, `upstream_4xx`, `connect_error`, `request_error`).
- Transient network classes and `5xx` receive bounded retry/backoff; terminal failures publish reconciliation issues with failure-class context.
- Lifecycle hardening (`DEV-00041`) enforces valid status transitions, stale/duplicate command rejection, and reconciliation SLA breach context fields (`sla_seconds`, `age_seconds`).
