# EPIC-23: Feature and Signal State Backbone

## Scope
- Establish first-class feature/signal persistence.
- Close HLD Section 6 gaps for `feature_snapshot`, `signal_score`, and `regime_state`.

## Deliverables
- Schema and contracts for feature snapshots, signal scores, and regime states.
- Online/offline consistency keys and timestamp semantics.
- Signal lineage checks from source features to scored outputs.

## Acceptance
- Every live signal can be traced to persisted feature and regime snapshots.

## Commit Slices
1. `feat(features): add feature_snapshot and signal_score schema`
2. `feat(regime): add regime_state lifecycle contracts`
3. `test(features): add feature-to-signal lineage validation`
