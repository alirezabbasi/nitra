# Signal Engine Baseline (DEV-00039)

## Purpose

Convert deterministic feature snapshots into deterministic scored signal decisions with explainability metadata.

## Runtime Placement

- Implemented in `services/inference-gateway/app.py` as the baseline scorer path.

## Inputs

- Kafka topic: `features.snapshot.v1`

## Outputs

- Kafka topic: `decision.signal_scored.v1`
- TimescaleDB table: `signal_score_log`

## Scoring Contract

- Deterministic linear scorer with fixed weights over feature keys.
- Threshold policy:
  - buy when `score >= SIGNAL_SCORE_THRESHOLD_BUY`
  - sell when `score <= SIGNAL_SCORE_THRESHOLD_SELL`
  - otherwise hold
- Confidence derived deterministically from absolute score with cap.

## Explainability Contract

Signal payload includes:

- `reason_codes` (traceable score rationale)
- `feature_refs.lineage`
- pinned version metadata:
  - `scorer.config_version`
  - `scorer.model_version`
  - `scorer.feature_set_version`

## Calibration Harness

- `run_calibration(samples)` computes deterministic score distribution report for validation.

## Validation

- `tests/dev-0039/run.sh`
- unit tests under `tests/dev-0039/unit`
