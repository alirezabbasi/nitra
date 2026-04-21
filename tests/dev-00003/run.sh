#!/usr/bin/env bash
set -euo pipefail

[[ -f infra/kafka/topics.csv ]]
[[ -x scripts/kafka/bootstrap-topics.sh ]]

rg -n '^raw.market.oanda,' infra/kafka/topics.csv >/dev/null
rg -n '^normalized.quote.fx,' infra/kafka/topics.csv >/dev/null
rg -n '^bar.1m,' infra/kafka/topics.csv >/dev/null
rg -n '^gap.events,' infra/kafka/topics.csv >/dev/null

rg -n -- '--if-not-exists' scripts/kafka/bootstrap-topics.sh >/dev/null
rg -n -- 'cleanup.policy=' scripts/kafka/bootstrap-topics.sh >/dev/null
rg -n -- 'retention.ms=' scripts/kafka/bootstrap-topics.sh >/dev/null

DRY_RUN=1 scripts/kafka/bootstrap-topics.sh >/tmp/nitra-dev-00003-dryrun.log
rg -n '\[kafka-bootstrap\] dry-run:' /tmp/nitra-dev-00003-dryrun.log >/dev/null

echo "[dev-00003] checks passed"
