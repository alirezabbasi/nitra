# Session Ledger

Append one entry at the end of each substantial session.

---

## 2026-04-23 — Session Entry 001

- Objective:
  - warm-up on project docs and assess HLD Section 5 implementation coverage.
- Work completed:
  - loaded mandatory rulesets and architecture baselines.
  - reviewed Section 5 top-down and mapped each architecture block to repository status.
  - committed completed kanban scope (`DEV-00001..DEV-00007`) under commit `f51c5f5`.
  - restructured `docs/development` into governance, roadmap, execution, delivery, and memory sections.
  - introduced persistent memory system files and update protocol.
- Key outcomes:
  - full-project orientation now available beyond ingestion-only tracking.
  - stable cross-session resume mechanism created.
- Next recommended action:
  - define and register next ticket batch for structure/risk/execution deterministic core.

---

## 2026-04-23 — Session Entry 002

- Objective:
  - embed a mandatory "Where are we?" command and reorganize `docs/` into a coherent system.
- Work completed:
  - added canonical docs entrypoints (`docs/README.md`, `docs/design/README.md`).
  - refreshed ingestion docs root readme for NITRA scope and clarified legacy context boundaries.
  - embedded "Where are we?" requirements in global ruleset, ingestion ruleset, governance model, and memory MOS.
  - added dedicated memory artifact `WHERE_ARE_WE.md` plus template.
  - de-duplicated development artifacts by moving reuse-map/runbook into canonical delivery artifacts path and leaving compatibility pointers.
  - fixed stale/broken doc references in ingestion devdocs and tickets.
- Key outcomes:
  - one coherent documentation navigation path now exists across design, development, and domain docs.
  - status reporting protocol is standardized and now enforceable from rulesets + memory system.
- Next recommended action:
  - open and execute the next deterministic-core ticket batch (structure/risk/execution/replay controller).

---

## 2026-04-23 — Session Entry 003

- Objective:
  - implement hard-gate Section 5.1 technology enforcement as executable project policy.
- Work completed:
  - added policy manifests under `policy/` for technology allocation and waiver lifecycle.
  - added hard gate scripts: `check_technology_enforcement.sh`, `check_contract_policy.sh`.
  - wired enforcement into Makefile via `policy-check` and `enforce-section-5-1`.
  - added contract LLD doc `09_ai_schema_contracts.md` and linked LLD index.
  - updated ADR/HLD/LLD and governance docs for waiver process + migration state model.
  - registered migration tickets `DEV-00010`, `DEV-00011`, `DEV-00012`.
  - integrated compliance tracking into roadmap/current-state/where-are-we/kanban.
  - added policy gate behavior tests (`tests/dev-0010/run.sh`).
- Verification:
  - `make policy-check` passes.
  - `tests/dev-0010/run.sh` passes.
  - existing dev checks pass (`dev-00003`, `dev-00004`, `dev-00005`, `dev-00006`, `dev-00008`, `dev-00009`) with `PYTHONPYCACHEPREFIX` workaround for local permission constraints.
- Next recommended action:
  - start implementation ticket `DEV-00010` (Rust migration of market ingestion connectors) with freeze on net-new deterministic Python scope.

---

## 2026-04-23 — Session Entry 004

- Objective:
  - execute `DEV-00010` and cut over market-ingestion deterministic connector runtime from Python to Rust.
- Work completed:
  - replaced `services/market-ingestion` Python runtime with Rust implementation (`Cargo.toml`, `src/main.rs`).
  - preserved envelope/payload semantics and existing ingestion env variable contract.
  - migrated `services/market-ingestion/Dockerfile` to compiled Rust binary runtime.
  - updated compose wiring for market-ingestion connector services.
  - updated policy manifest: `market_ingestion_connectors` now `compliant` with `current_runtime: rust`.
  - updated ticket/kanban/roadmap/memory artifacts to reflect migration completion.
  - updated `tests/dev-00005/run.sh` to validate Rust connector path.
- Verification:
  - `make enforce-section-5-1` passes.
  - `tests/dev-00005/run.sh` passes.
  - `tests/dev-0010/run.sh` passes.
- Next recommended action:
  - execute `DEV-00011` (Rust migration for market normalization/replay).

---

## 2026-04-23 — Session Entry 005

- Objective:
  - execute `DEV-00011` and cut over market-normalization/replay deterministic runtime from Python to Rust.
- Work completed:
  - replaced `services/market-normalization` Python runtime with Rust implementation (`Cargo.toml`, `src/main.rs`).
  - preserved normalization output envelope/fields, canonical symbol mapping fallback, and dedup semantics.
  - preserved manual commit processing with explicit commit lifecycle and replay-safe ledger checks.
  - migrated `services/market-normalization/Dockerfile` to compiled Rust binary runtime.
  - updated compose symbol-registry mount path for binary runtime deployment.
  - updated policy manifest: `market_normalization_replay` now `compliant` with `current_runtime: rust`.
  - updated ticket/kanban/roadmap/memory artifacts for migration completion.
  - updated `tests/dev-00005/run.sh` and `tests/dev-00006/run.sh` for Rust validation.
- Verification:
  - `cargo check --manifest-path services/market-normalization/Cargo.toml` passes.
  - `tests/dev-00005/run.sh` passes.
  - `tests/dev-00006/run.sh` passes.
  - `DEV00006_INTEGRATION=1 tests/dev-00006/run.sh` passes.
  - `tests/dev-0010/run.sh` passes.
  - `make enforce-section-5-1` passes.
- Next recommended action:
  - execute `DEV-00012` (Rust migration for bar aggregation + gap detection + backfill controller).

---

## 2026-04-23 — Session Entry 006

- Objective:
  - execute `DEV-00012` and cut over bar aggregation, gap detection, and backfill deterministic services from Python to Rust.
- Work completed:
  - replaced Python runtimes in `services/bar-aggregation`, `services/gap-detection`, and `services/backfill-worker` with Rust implementations.
  - preserved stream contracts and deterministic flow (`normalized.quote.fx` -> `bar.1m` -> `gap.events` -> `replay.commands`).
  - preserved replay-safe ledger semantics with explicit dedup checks and `ON CONFLICT DO NOTHING` ledger writes.
  - migrated all three service Dockerfiles to compiled Rust binary runtimes.
  - updated compose runtime mounts for binary deployment.
  - updated policy manifest: `bar_gap_backfill` now `compliant` with `current_runtime: rust`.
  - retired waiver `WVR-0003` and updated ticket/kanban/roadmap/memory docs.
  - updated dev checks and added `tests/dev-0012` migration test pack (+ integration script).
- Verification:
  - `cargo check --manifest-path services/bar-aggregation/Cargo.toml` passes.
  - `cargo check --manifest-path services/gap-detection/Cargo.toml` passes.
  - `cargo check --manifest-path services/backfill-worker/Cargo.toml` passes.
  - `tests/dev-00005/run.sh` passes.
  - `tests/dev-00006/run.sh` passes.
  - `tests/dev-0010/run.sh` passes.
  - `tests/dev-0012/run.sh` passes.
  - `DEV0012_INTEGRATION=1 tests/dev-0012/run.sh` passes.
  - `make enforce-section-5-1` passes.
- Next recommended action:
  - begin deterministic runtime implementation for `structure-engine`, then `risk-engine` and `execution-gateway`.

---

## 2026-04-23 — Session Entry 007

- Objective:
  - fix charting live-candle correctness and UI usability before next deterministic core planning slice.
- Work completed:
  - patched `/api/v1/ticks/hot` query strategy to fetch freshest ticks (DESC query with ASC response order for client merge).
  - rewrote chart frontend live-merge logic to prevent historical candle mutation and remove synthetic flat-gap candles.
  - adjusted live cursor handling to anchor after last persisted bar, improving current-candle alignment.
  - added chart fit routine on live updates/resizes for consistent visible-range scaling behavior.
  - removed sidebar market picker and implemented header dropdown selectors (venue + instrument).
- Verification:
  - structural checks of updated charting API/UI paths.
  - python syntax check attempted for `services/charting/app.py`; local pycache permission constraint observed (same environment limitation as prior sessions).
- Next recommended action:
  - run live chart smoke validation via compose and confirm candle OHLC parity against `raw_tick`/`ohlcv_bar` in DB.

---

## 2026-04-23 — Session Entry 008

- Objective:
  - make chart market selection searchable and restore working multi-timeframe rendering.
- Work completed:
  - replaced fixed market `<select>` with searchable input+datalist (`venue · instrument`).
  - restored timeframe controls (`1m`, `5m`, `15m`, `1h`) and click handler flow.
  - fixed timeframe switch behavior to keep prior market when available and fallback to first available market for the new timeframe.
  - added fallback loading path: when higher timeframe bars are unavailable in storage, fetch `1m` bars and aggregate client-side to requested timeframe.
  - added market list fallback: if `markets/available` is empty for higher timeframe, use `1m` availability to keep selector usable.
- Verification:
  - live check (inside charting container) confirmed current data shape: `1m` markets available, `5m/15m/1h` markets empty in DB-backed endpoint.
  - source sanity checks passed for updated UI/event/fallback paths in `services/charting/static/index.html`.
- Next recommended action:
  - decide whether to persist native `5m/15m/1h` bars in backend aggregation, or keep client-side derivation as intended runtime behavior.

---

## 2026-04-23 — Session Entry 009

- Objective:
  - formalize business requirement for startup historical coverage (rolling 90 days of `1m` candles) and create executable delivery tasking.
- Work completed:
  - reviewed docs to locate existing references; confirmed retention references existed but no explicit startup enforcement rule.
  - updated HLD (`Section 6.2`) with mandatory startup coverage enforcement for active instruments.
  - updated LLD service catalog (bar aggregation + gap/backfill) with mandatory startup audit/backfill behavior.
  - created delivery ticket `DEV-00013` for implementation of startup coverage audit + missing-only broker backfill.
  - updated roadmap and kanban to prioritize `DEV-00013`.
  - synchronized memory files (`CURRENT_STATE`, `WHERE_ARE_WE`) to reflect the new policy and next action.
- Key outcomes:
  - 90-day `1m` chart-history requirement is now explicit in architecture governance, not implicit retention guidance.
  - implementation path is now tracked and visible in execution/memory systems.
- Next recommended action:
  - start `DEV-00013` implementation in deterministic Rust backfill path with startup readiness gating.

---

## 2026-04-23 — Session Entry 010

- Objective:
  - implement `DEV-00013` runtime baseline for startup 90-day `1m` coverage enforcement and deterministic missing-only backfill orchestration.
- Work completed:
  - rewrote `services/gap-detection` with startup coverage scan (`90d` window by default), active-market discovery (registry + DB), gap persistence (`gap_log`), event emission (`gap.events`), and coverage state tracking (`coverage_state`).
  - rewrote `services/backfill-worker` to process startup/open gaps and stream gaps, split into deterministic chunks, persist `backfill_jobs`, write `replay_audit`, and publish enriched `replay.commands`.
  - added runtime schema migration `infra/timescaledb/init/004_gap_backfill_runtime.sql` for `coverage_state`, `gap_log`, `backfill_jobs`, and `replay_audit`.
  - updated compose environment contracts for new startup scan/backfill controls and mounted symbol registry into `gap-detection`.
  - added delivery validation script `tests/dev-0013/run.sh` and make target `test-dev-0013`.
  - updated ingestion env documentation and live runbook with startup coverage/gap/backfill verification commands.
  - updated kanban/memory state to reflect `DEV-00013` implementation progress.
- Verification:
  - `cargo test --manifest-path services/gap-detection/Cargo.toml` passes.
  - `cargo test --manifest-path services/backfill-worker/Cargo.toml` passes.
- Next recommended action:
  - implement replay-controller execution for `replay.commands` to fully close the broker-history backfill loop end-to-end.

---

## 2026-04-24 — Session Entry 011

- Objective:
  - implement replay-controller execution step for `DEV-00013` so queued replay jobs materialize bars and update lifecycle state.
- Work completed:
  - added new deterministic Rust service `services/replay-controller` (Kafka consumer for `replay.commands`).
  - implemented replay execution path:
    - parse replay commands and ranges,
    - aggregate `raw_tick` into minute OHLC,
    - upsert `ohlcv_bar`,
    - update `backfill_jobs` (`running`/`completed`/`partial`/`failed_no_source_data`),
    - update `replay_audit` completion/error fields,
    - resolve covered `gap_log` rows when ranges become complete.
  - wired `replay-controller` into `docker-compose.yml` with registry mount and environment contract.
  - updated policy manifest (`policy/technology-allocation.yaml`) and LLD service catalog to register replay-controller under deterministic core.
  - updated ingestion env docs, live runbook, and `DEV-00013` ticket notes.
  - extended `tests/dev-0013/run.sh` to validate replay-controller presence and tests.
- Verification:
  - replay-controller unit tests pass.
  - updated `tests/dev-0013/run.sh` passes.
  - `make enforce-section-5-1` passes with replay-controller policy registration.
- Next recommended action:
  - add broker-history source adapters for ranges where `raw_tick` does not yet hold full 90-day history.

---

## 2026-04-24 — Session Entry 012

- Objective:
  - execute venue-history completion items for 90-day backfill and formalize continuity policy decision.
- Work completed:
  - created delivery ticket `DEV-00014` for venue-history adapters and session-aware continuity policy.
  - implemented charting backfill runtime updates in `services/charting/app.py`:
    - Capital REST history adapter (`POST /api/v1/session` + `GET /api/v1/prices/{epic}` with session refresh),
    - Coinbase fallback route from Exchange candles endpoint to Advanced Trade public candles endpoint,
    - session-aware continuity policy:
      - FX venues (`oanda`, `capital`) exclude weekend-closed minutes from required continuity,
      - crypto venues require full `24/7` minute continuity.
  - expanded charting compose/env contract for new adapter credentials/endpoints and runtime controls.
  - updated HLD/LLD and devdocs with continuity-policy decision and adapter routing details.
  - added baseline test pack `tests/dev-0014/run.sh` and Make target `test-dev-0014`.
- Verification:
  - Python syntax checks pass for `services/charting/app.py`.
  - live backfill probes executed for `oanda`, `coinbase`, and `capital` with explicit response diagnostics.
- Next recommended action:
  - complete live adapter hardening (network/runtime edge cases) and promote `DEV-00014` from in-progress to done.

---

## 2026-04-24 — Session Entry 013

- Objective:
  - validate reported ingestion/runtime mismatch against implementation and docs (Coinbase price realism + 90-day backfill behavior).
- Work completed:
  - reloaded required project/ruleset/HLD context and audited ingestion/backfill implementation paths.
  - verified `market-ingestion` runtime currently emits synthetic random quotes and tags events with `source = nitra.market_ingestion.mock`.
  - captured live DB evidence showing Coinbase `raw_tick` rows are mock-sourced.
  - captured live backfill status evidence showing dominant `failed_no_source_data`/`failed` states in `backfill_jobs` and `replay_audit`.
  - confirmed deterministic replay path rebuilds bars from available `raw_tick` only (no broker-history fetch in replay controller).
  - validated current test packs (`tests/dev-0013/run.sh`, `tests/dev-0014/run.sh`) pass but do not assert live venue-price correctness.
  - registered new ingestion bugs:
    - `BUG-00005` (Coinbase live feed still mock-generated)
    - `BUG-00006` (startup 90-day backfill stalls on source-depth gaps)
  - updated memory snapshot with audit findings and risks.
- Verification:
  - live SQL evidence from running compose stack (coinbase rows + backfill/replay/gap statuses).
  - charting API probes for Coinbase ticks/bars and backfill timeout behavior.
  - `tests/dev-0013/run.sh` passes.
  - `tests/dev-0014/run.sh` passes.
- Next recommended action:
  - implement real venue ingestion adapter path (starting with Coinbase) and add replay-controller broker-history fetch adapters to close `BUG-00005` and `BUG-00006`.

---

## 2026-04-24 — Session Entry 014

- Objective:
  - enforce strict no-mock ingestion policy and ensure venue connectors ingest only venue-sourced prices.
- Work completed:
  - rewrote `services/market-ingestion/src/main.rs` to remove synthetic/random quote generation entirely.
  - implemented venue-sourced ingestion fetch paths:
    - Coinbase ticker API (`/products/{product}/ticker`)
    - OANDA pricing API (`/v3/accounts/{account}/pricing`)
    - Capital authenticated price fetch (`/api/v1/session` + `/api/v1/prices/{epic}?resolution=MINUTE&max=1`)
  - enforced fail-closed connector policy: `CONNECTOR_MODE=mock` now aborts startup.
  - removed obsolete runtime mock module: `services/ingestion/mock_pricing.py`.
  - updated ingestion guard tests:
    - `tests/dev-00005/run.sh` now checks no mock/random ingestion code patterns
    - `tests/dev-00009/run.sh` repurposed as no-mock regression guard
  - updated ingestion docs and bug registry state to reflect no-mock runtime policy and resolution status for `BUG-00005`.
- Verification:
  - `cargo check --manifest-path services/market-ingestion/Cargo.toml` passes.
  - `tests/dev-00005/run.sh` passes.
  - `tests/dev-00009/run.sh` passes.
- Next recommended action:
  - restart ingestion services and validate live DB samples (`raw_tick.source`) show only `nitra.market_ingestion.<venue>` sources for active venues.

---

## 2026-04-24 — Session Entry 015

- Objective:
  - close ingestion connector correction commit and implement chart interaction UX parity upgrade.
- Work completed:
  - committed ingestion correction batch (`2adcc4d`) including no-mock guardrails, connector runtime fixes, and bug registry updates.
  - created ticket `DEV-00015` for chart interaction UX parity (15 feature set).
  - implemented charting backend pagination endpoint `GET /api/v1/bars/history` for left-edge historical loading.
  - implemented chart UX upgrades in `services/charting/static/index.html`:
    - realtime return button,
    - jump-to-timestamp and jump-to-index,
    - zoom-anchor selector,
    - bar-space + right-offset controls,
    - left/right min visible bars controls,
    - zoom/scroll lock toggles,
    - range/crosshair metadata subscriptions,
    - coordinate/value inspector via pixel conversion,
    - snapshot export,
    - locale/timezone and number-format controls,
    - lazy history loading while maintaining live tick polling.
  - added `DEV-00015` test pack and Make target wiring.
- Verification:
  - `PYTHONPYCACHEPREFIX=/tmp python -m py_compile services/charting/app.py`
  - `tests/dev-0015/run.sh`
- Next recommended action:
  - run live browser validation for mobile/desktop interaction ergonomics and tune control defaults.
