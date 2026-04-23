# Gap Coverage and Precision Backfill (EPIC-06)

## Objective

Detect missing 1-minute bar intervals and generate precise, chunked backfill/replay jobs for only the missing windows.

## Gap Engine

Input:
- `bar.1m` (`Envelope<Bar>`)

Output:
- `gap.events` (`Envelope<GapEvent>`)

Behavior:
- Tracks last seen bucket per `(venue, canonical_symbol)`.
- Detects stream-time gaps when current bucket skips expected minute.
- Performs startup internal scan over recent hot-store bars and emits internal gaps.
  - This is the recovery path after outages/restarts.
  - Scan depth is controlled by `GAP_ENGINE_STARTUP_SCAN_HOURS` and must be sized to cover expected downtime windows.
- Writes coverage state and gap log rows in TimescaleDB.
- De-duplicates gap emissions using unique DB constraint.

## Backfill Worker

Input:
- `gap.events` (`Envelope<GapEvent>`)

Output:
- `replay.commands` (`Envelope<ReplayRequest>`)

Behavior:
- Acquires symbol-level advisory lock to avoid concurrent duplicate processing.
- Splits exact gap window into deterministic chunks (`BACKFILL_FETCH_CHUNK_MINUTES`).
- Persists `backfill_jobs` rows for each chunk.
- Emits replay commands for each chunk range.
- Records replay audit rows.
- Marks gap status as `backfill_queued`.
- End-to-end effect: once engine processing resumes, missed OHLCV windows are detected and replay/backfilled so chart history remains continuous.

## Data Persistence

EPIC-06 adds persistent metadata tables:
- `coverage_state`
- `gap_log`
- `backfill_jobs`
- `replay_audit`

No destructive deletion behavior is used in this workflow.
