# AI Trading System — Full LLD Pack

This package contains the Low-Level Design (LLD) artifacts for the AI-enabled trading system.

## Contents
- `01_service_catalog.md`
- `02_repository_structure.md`
- `03_openapi_contracts.md`
- `04_asyncapi_event_contracts.md`
- `05_database_schema_v1.md`
- `06_state_machines.md`
- `07_deployment_topology.md`
- `08_slos_alerting_runbooks.md`

## Intended Use
This package is the implementation baseline for:
- backend engineering
- platform engineering
- quant/ML engineering
- SRE/DevOps
- architecture governance

## Design Rules
- Deterministic structural logic is implemented in Rust.
- Risk policy is authoritative over all model outputs.
- LLM/RAG is advisory, schema-constrained, and auditable.
- Research and live execution paths remain separated.
