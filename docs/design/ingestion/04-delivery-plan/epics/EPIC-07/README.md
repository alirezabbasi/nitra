# EPIC-07: Lakehouse Archive (MinIO/S3)

## Scope
- Archive immutable datasets to Parquet with idempotency proof.
- Maintain checkpoints and manifest integrity.

## Deliverables
- Archive writer service.
- Manifest/checksum schema.
- Archive integrity verification flow without destructive hot-data deletion by default.

## Acceptance
- Archive reruns are idempotent and checksum-verified.

## Commit Slices
1. `feat(archive): add parquet writer and partition strategy`
2. `feat(archive): add manifest checkpoints and integrity verifier`
