# 09 — AI Schema Contracts

## Purpose

Define schema enforcement requirements for probabilistic/AI services so Rust deterministic services and Python AI services do not drift.

## Mandatory Policy

- All AI-facing request/response payloads must be schema-validated at runtime.
- Python AI services must use Pydantic (or equivalent JSON Schema validation) for request and response models.
- Event payloads emitted to stream backbone must be versioned and documented in AsyncAPI artifacts.

## Minimum Requirements

1. Every AI service endpoint has explicit request/response schema objects.
2. Runtime validation failure must return explicit structured error output.
3. Schema version must be included in emitted AI event payloads.
4. Backward-incompatible schema changes require version increment and migration notes.
