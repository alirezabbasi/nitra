# Risks and Assumptions Register

Last updated: 2026-04-23

## Risks

### RISK-0001: Architecture drift toward ingestion-only evolution

- Severity: high
- Probability: medium
- Description: project momentum may stay confined to ingestion and delay deterministic core modules.
- Mitigation:
  - maintain HLD-aligned roadmap status table
  - prioritize next ticket batch for structure/risk/execution

### RISK-0002: Session context loss across long gaps

- Severity: high
- Probability: high
- Description: without persistent memory updates, priorities and assumptions may diverge over time.
- Mitigation:
  - mandatory session ledger updates
  - mandatory refresh of `CURRENT_STATE.md` before closing sessions

### RISK-0003: Over-scoped implementation slices
- Severity: medium
- Probability: medium
- Description: large multi-module changes can reduce traceability and quality.
- Mitigation:
  - enforce small, step-based tickets
  - implementation -> tests -> docs sequence per slice

## Assumptions

### ASM-0001

- Statement: Docker Compose remains the primary dev runtime for the near-term delivery window.
- Confidence: high

### ASM-0002

- Statement: Deterministic risk/execution boundaries remain authoritative over AI outputs.
- Confidence: high

### ASM-0003

- Statement: Ticket IDs continue with `DEV-XXXXX` format for current phase.
- Confidence: high
