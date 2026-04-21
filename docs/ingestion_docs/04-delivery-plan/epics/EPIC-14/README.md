# EPIC-14: Rust Hot-Path Optimization

## Scope
- Apply Rust-specific optimizations for serialization, parsing, and memory behavior.
- Reduce allocation and parsing overhead in connector/normalizer pipelines.

## Deliverables
- Typed contract refinements (timestamp and payload shape hardening).
- Hot-path serde/JSON optimization plan and implementation.
- Baseline and post-change microbench results.

## Acceptance
- Throughput and tail-latency improve measurably on fixed load profiles.

## Commit Slices
1. `refactor(contracts): harden typed event fields for hot paths`
2. `perf(pipeline): reduce alloc and parse overhead in ingest/normalize`
