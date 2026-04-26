BEGIN;

-- One-time safe cleanup for legacy unknown-market backlog rows.
-- Safety model:
-- 1) no deletes;
-- 2) status-only updates;
-- 3) restricted to non-registry markets.

WITH registry(venue, canonical_symbol) AS (
  VALUES
    ('oanda','EURUSD'),('oanda','GBPUSD'),('oanda','USDJPY'),('oanda','NAS100'),('oanda','US30'),('oanda','XAUUSD'),
    ('capital','EURUSD'),('capital','GBPUSD'),('capital','NAS100'),('capital','US30'),('capital','XAUUSD'),
    ('coinbase','BTCUSD'),('coinbase','ETHUSD'),('coinbase','SOLUSD'),('coinbase','ADAUSD'),('coinbase','XRPUSD')
), unknown_jobs AS (
  SELECT bj.job_id
  FROM backfill_jobs bj
  LEFT JOIN registry r
    ON r.venue = bj.venue
   AND r.canonical_symbol = bj.canonical_symbol
  WHERE r.venue IS NULL
), update_backfill AS (
  UPDATE backfill_jobs bj
  SET status = 'failed_unknown_market',
      updated_at = now()
  WHERE bj.job_id IN (SELECT job_id FROM unknown_jobs)
    AND bj.status IN ('queued', 'running', 'partial', 'failed_no_source_data')
  RETURNING bj.job_id
), update_replay AS (
  UPDATE replay_audit ra
  SET status = 'failed',
      completed_at = COALESCE(ra.completed_at, now()),
      error = COALESCE(NULLIF(ra.error, ''), 'legacy unknown market cleanup'),
      moved_messages = COALESCE(ra.moved_messages, 0)
  WHERE ra.replay_id IN (SELECT job_id FROM unknown_jobs)
    AND ra.status IN ('queued', 'partial')
  RETURNING ra.replay_id
), update_gaps AS (
  UPDATE gap_log gl
  SET status = 'ignored_unknown_market',
      updated_at = now(),
      resolved_at = COALESCE(gl.resolved_at, now())
  WHERE EXISTS (
    SELECT 1
    FROM registry r
    WHERE r.venue = gl.venue
      AND r.canonical_symbol = gl.canonical_symbol
  ) IS FALSE
    AND gl.status IN ('open', 'backfill_queued')
  RETURNING gl.gap_id
)
SELECT
  (SELECT COUNT(*) FROM unknown_jobs) AS unknown_jobs_total,
  (SELECT COUNT(*) FROM update_backfill) AS backfill_rows_marked_failed_unknown_market,
  (SELECT COUNT(*) FROM update_replay) AS replay_rows_marked_failed,
  (SELECT COUNT(*) FROM update_gaps) AS gap_rows_marked_ignored_unknown_market;

COMMIT;
