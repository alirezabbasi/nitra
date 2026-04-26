# Simplified Gap Detection + Auto Backfill Redesign

## Why redesign

Current behavior is functionally rich but operationally heavy:

- too many moving states across `gap_log`, `backfill_jobs`, `replay_audit`,
- broad market discovery can enqueue work outside intended symbol scope,
- retry/re-enqueue loops can amplify backlog when inputs are invalid or source depth is limited,
- difficult to quickly answer: "which symbols are blocked and why?"

This redesign keeps existing service boundaries (`gap-detection` -> `backfill-worker` -> `replay-controller`) but simplifies control logic and reduces queue amplification.

## Design principles

1. Registry-first scope
- Coverage/backfill must be driven by canonical registry mappings.
- Unknown `(venue, canonical_symbol)` pairs are not recoverable work; treat them as config errors, not replay workload.

2. One clear backlog truth
- `backfill_jobs` is the execution queue.
- `gap_log` is detection evidence.
- `replay_audit` is attempt/result evidence.

3. Bounded work generation
- Never generate unlimited new chunks for the same symbol while unresolved work exists.
- Prioritize oldest unresolved ranges first.

4. Fail-closed on bad configuration
- Invalid market mappings should stop at ingestion/backfill edge with explicit status, not churn forever in retry loops.

## Practical simplified flow

1. Gap detection (planner)
- Inputs: `bar.1m`, registry.
- Responsibilities:
  - update `coverage_state`,
  - detect missing ranges,
  - insert one gap record per missing range (`gap_log`),
  - emit gap events only for registry-approved markets.
- Simplification:
  - default to registry-scoped scans (`GAP_INCLUDE_DB_DISCOVERED_MARKETS=false`).

2. Backfill worker (queue manager)
- Inputs: `gap.events`, registry.
- Responsibilities:
  - split ranges into bounded chunk jobs (`backfill_jobs`),
  - enqueue replay commands,
  - keep stale recovery bounded with backpressure.
- Simplification:
  - reject unknown markets early and mark gap as ignored (`ignored_unknown_market`).

3. Replay controller (executor)
- Inputs: `replay.commands`, registry.
- Responsibilities:
  - build bars from `raw_tick`,
  - fallback to venue history adapter,
  - set terminal/partial statuses,
  - resolve gaps when complete.
- Simplification:
  - fail unknown markets immediately (`failed_unknown_market`) to prevent requeue churn.

## Immediate changes applied

- Registry corrected to remove invalid Coinbase EURUSD mapping.
- Registry expanded for active OANDA/CAPITAL index/metals mappings:
  - OANDA: `NAS100_USD`, `US30_USD`, `XAU_USD`
  - CAPITAL: `US100`, `US30`, `GOLD`
- `gap-detection` now defaults to registry-only planning (`GAP_INCLUDE_DB_DISCOVERED_MARKETS=false`).
- `backfill-worker` now enforces registry guardrails before creating replay load.
- `replay-controller` now fails unknown markets fast instead of processing/retrying.

## Next rollout steps

1. Backlog cleanup pass (one-time)
- Mark legacy unknown-market jobs as terminal to stop unnecessary retries.
- Keep valid queued jobs untouched.

2. Add explicit terminal taxonomy
- Consolidate terminal statuses:
  - `completed`,
  - `partial`,
  - `failed_no_source_data`,
  - `failed_unknown_market`,
  - `ignored_unknown_market`.

3. Add single "coverage debt" query/report
- Per symbol: expected minutes (window) vs present minutes, oldest missing span, queue status.
- This becomes the primary operator view for recovery progress.

4. Reduce periodic scan fanout further
- Add per-symbol cooldown for repeated periodic gap inserts when status already unresolved.
- Keep startup scan for baseline, periodic scan for drift only.

## Success criteria

- Queue growth stabilizes (no continuous increase from invalid symbols).
- Unknown-market jobs become near-zero after cleanup.
- Coverage convergence prioritizes valid symbols with deterministic progress.
- Operators can explain missing data per symbol from one report.
