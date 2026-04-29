#!/usr/bin/env bash
set -euo pipefail

[[ -f services/execution-gateway/src/main.rs ]]
[[ -f docker-compose.yml ]]
[[ -f docs/design/ingestion/07-devdocs/01-development-environment/ingestion-service-env.md ]]
[[ -f docs/design/nitra_system_lld/01_service_catalog.md ]]

cargo fmt --manifest-path services/execution-gateway/Cargo.toml -- --check
CARGO_TARGET_DIR=/tmp/nitra-execution-gateway-target cargo check --offline --manifest-path services/execution-gateway/Cargo.toml
CARGO_TARGET_DIR=/tmp/nitra-execution-gateway-target cargo test --offline --manifest-path services/execution-gateway/Cargo.toml

rg -n 'EXEC_BROKER_RETRY_MAX_ATTEMPTS|EXEC_BROKER_RETRY_BACKOFF_MS|EXEC_BROKER_RETRY_BACKOFF_CAP_MS|EXEC_BROKER_DEGRADED_COOLDOWN_MS' docker-compose.yml >/dev/null
rg -n 'classify_reqwest_error|classify_http_status|attempt_backoff_ms|failure_class|adapter_terminal_failure|adapter_command_failure' services/execution-gateway/src/main.rs >/dev/null
rg -n 'dns_resolution|connect_timeout|io_timeout|upstream_5xx' docs/design/ingestion/07-devdocs/01-development-environment/ingestion-service-env.md >/dev/null

echo "[dev-0022] checks passed"
