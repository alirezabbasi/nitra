#!/usr/bin/env bash
set -euo pipefail

TOPICS_FILE="${TOPICS_FILE:-infra/kafka/topics.csv}"
BOOTSTRAP_SERVER="${BOOTSTRAP_SERVER:-kafka:9092}"
DRY_RUN="${DRY_RUN:-0}"

if [[ ! -f "$TOPICS_FILE" ]]; then
  echo "[kafka-bootstrap] topics file not found: $TOPICS_FILE" >&2
  exit 1
fi

run_topic_create() {
  local name="$1"
  local partitions="$2"
  local replication_factor="$3"
  local cleanup_policy="$4"
  local retention_ms="$5"

  local cmd=(
    docker compose exec -T kafka /opt/kafka/bin/kafka-topics.sh
    --bootstrap-server "$BOOTSTRAP_SERVER"
    --create
    --if-not-exists
    --topic "$name"
    --partitions "$partitions"
    --replication-factor "$replication_factor"
    --config "cleanup.policy=$cleanup_policy"
    --config "retention.ms=$retention_ms"
  )

  if [[ "$DRY_RUN" == "1" ]]; then
    printf '[kafka-bootstrap] dry-run:'
    printf ' %q' "${cmd[@]}"
    printf '\n'
  else
    "${cmd[@]}"
  fi
}

while IFS=, read -r name partitions replication_factor cleanup_policy retention_ms _rest; do
  [[ -z "${name:-}" ]] && continue
  [[ "${name:0:1}" == "#" ]] && continue

  run_topic_create "$name" "$partitions" "$replication_factor" "$cleanup_policy" "$retention_ms"
done < "$TOPICS_FILE"

if [[ "$DRY_RUN" != "1" ]]; then
  docker compose exec -T kafka /opt/kafka/bin/kafka-topics.sh \
    --bootstrap-server "$BOOTSTRAP_SERVER" \
    --list
fi
