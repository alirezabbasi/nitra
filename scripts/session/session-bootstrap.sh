#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

MAX_STALENESS_DAYS="${SESSION_MAX_STALENESS_DAYS:-7}"

fail() {
  printf 'SESSION_BOOTSTRAP_FAIL: %s\n' "$1" >&2
  exit 1
}

check_file() {
  local path="$1"
  [[ -f "$path" ]] || fail "required file missing: $path"
}

check_dir() {
  local path="$1"
  [[ -d "$path" ]] || fail "required directory missing: $path"
}

extract_last_updated() {
  local path="$1"
  local value
  value="$(grep -E '^Last updated:' "$path" | head -n1 | sed -E 's/^Last updated:[[:space:]]*//')"
  [[ -n "$value" ]] || fail "missing 'Last updated:' header in $path"
  printf '%s\n' "$value"
}

extract_latest_ledger_date() {
  local path="$1"
  local value
  value="$(grep -E '^## [0-9]{4}-[0-9]{2}-[0-9]{2} — Session Entry [0-9]+' "$path" | tail -n1 | sed -E 's/^## ([0-9]{4}-[0-9]{2}-[0-9]{2}).*$/\1/')"
  [[ -n "$value" ]] || fail "cannot find a session entry heading in $path"
  printf '%s\n' "$value"
}

days_since() {
  local iso_date="$1"
  local now_epoch date_epoch
  now_epoch="$(date +%s)"
  date_epoch="$(date -d "$iso_date" +%s 2>/dev/null)" || fail "invalid date '$iso_date' (expected YYYY-MM-DD)"
  printf '%s\n' "$(((now_epoch - date_epoch) / 86400))"
}

assert_heading() {
  local path="$1"
  local heading="$2"
  grep -Eq "^${heading}$" "$path" || fail "missing heading '${heading}' in $path"
}

validate_ticket_dod() {
  local tickets_dir="docs/development/tickets"
  local missing=()
  local file status

  shopt -s nullglob
  for file in "$tickets_dir"/DEV-*.md; do
    status="$(awk '
      /^## Status$/ { capture=1; next }
      capture && /^## / { capture=0 }
      capture && NF { print; exit }
    ' "$file" | tr -d '\r')"
    [[ -z "$status" ]] && status="MISSING"

    case "$status" in
      Done*|Merged\ into*|Split\ into*)
        continue
        ;;
    esac

    if ! grep -Eq '^## Definition of Done$' "$file"; then
      missing+=("${file#${ROOT_DIR}/}")
    fi
  done
  shopt -u nullglob

  if (( ${#missing[@]} > 0 )); then
    printf 'SESSION_BOOTSTRAP_FAIL: missing ticket DoD section in non-completed scope:\n' >&2
    printf ' - %s\n' "${missing[@]}" >&2
    exit 1
  fi
}

printf '[session-bootstrap] validating required context files...\n'

check_file "docs/README.md"
check_file "docs/ruleset.md"
check_file "docs/design/nitra_system_hld.md"
check_file "docs/design/AI-enabled_trading_decision_platform.md"
check_dir "docs/design/nitra_system_lld"
check_file "docs/design/nitra_system_lld/00_README.md"
check_file "docs/design/ingestion/ruleset.md"
check_file "docs/development/04-memory/WHERE_ARE_WE.md"
check_file "docs/development/04-memory/CURRENT_STATE.md"
check_file "docs/development/04-memory/SESSION_LEDGER.md"
check_file "docs/development/02-execution/KANBAN.md"
check_file "docs/development/02-execution/ACTIVE_FOCUS.md"

if [[ -f "AGENTS.md" ]]; then
  printf '[session-bootstrap] repository instructions detected: AGENTS.md\n'
else
  printf '[session-bootstrap] AGENTS.md not present at repository root (allowed by ruleset when absent).\n'
fi

printf '[session-bootstrap] validating required status structure...\n'
assert_heading "docs/development/04-memory/CURRENT_STATE.md" "### Completed"
assert_heading "docs/development/04-memory/CURRENT_STATE.md" "### Recent"
assert_heading "docs/development/04-memory/CURRENT_STATE.md" "### Current"
assert_heading "docs/development/04-memory/CURRENT_STATE.md" "### Next"
assert_heading "docs/development/04-memory/CURRENT_STATE.md" "### Risks/Blocks"

assert_heading "docs/development/04-memory/WHERE_ARE_WE.md" "## Completed"
assert_heading "docs/development/04-memory/WHERE_ARE_WE.md" "## Recent"
assert_heading "docs/development/04-memory/WHERE_ARE_WE.md" "## Current"
assert_heading "docs/development/04-memory/WHERE_ARE_WE.md" "## Next"
assert_heading "docs/development/04-memory/WHERE_ARE_WE.md" "## Risks/Blocks"

assert_heading "docs/development/02-execution/KANBAN.md" "## Backlog"
assert_heading "docs/development/02-execution/KANBAN.md" "## In Progress"
assert_heading "docs/development/02-execution/KANBAN.md" "## Done"
assert_heading "docs/development/02-execution/KANBAN.md" "## Blocked"

printf '[session-bootstrap] validating ticket DoD enforcement...\n'
validate_ticket_dod

printf '[session-bootstrap] validating memory freshness and drift...\n'

current_state_date="$(extract_last_updated "docs/development/04-memory/CURRENT_STATE.md")"
where_are_we_date="$(extract_last_updated "docs/development/04-memory/WHERE_ARE_WE.md")"
kanban_date="$(extract_last_updated "docs/development/02-execution/KANBAN.md")"
latest_ledger_date="$(extract_latest_ledger_date "docs/development/04-memory/SESSION_LEDGER.md")"

[[ "$current_state_date" == "$where_are_we_date" ]] || fail "memory drift: CURRENT_STATE ($current_state_date) != WHERE_ARE_WE ($where_are_we_date)"
[[ "$current_state_date" == "$kanban_date" ]] || fail "memory drift: CURRENT_STATE ($current_state_date) != KANBAN ($kanban_date)"
[[ "$current_state_date" == "$latest_ledger_date" ]] || fail "memory drift: CURRENT_STATE ($current_state_date) != latest SESSION_LEDGER entry ($latest_ledger_date)"

staleness_days="$(days_since "$current_state_date")"
if (( staleness_days > MAX_STALENESS_DAYS )); then
  fail "memory freshness exceeded: CURRENT_STATE is ${staleness_days} days old (limit ${MAX_STALENESS_DAYS})"
fi

printf '[session-bootstrap] context check passed.\n'
printf '[session-bootstrap] Last updated date: %s (staleness: %s days)\n' "$current_state_date" "$staleness_days"
printf '[session-bootstrap] Read order:\n'
printf '1. docs/README.md\n'
printf '2. docs/ruleset.md\n'
printf '3. docs/design/nitra_system_hld.md\n'
printf '4. docs/design/AI-enabled_trading_decision_platform.md\n'
printf '5. docs/design/nitra_system_lld/00_README.md\n'
printf '6. docs/design/ingestion/ruleset.md\n'
printf '7. docs/development/04-memory/WHERE_ARE_WE.md\n'
printf '8. docs/development/04-memory/CURRENT_STATE.md\n'
printf '9. docs/development/04-memory/SESSION_LEDGER.md\n'
printf '10. docs/development/02-execution/KANBAN.md\n'
printf '11. docs/development/02-execution/ACTIVE_FOCUS.md\n'
printf 'SESSION_BOOTSTRAP_OK\n'
