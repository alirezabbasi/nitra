# 10 — Interpretation Governance Artifacts (LLD)

## 1. Purpose

This document defines the mandatory low-level design contracts for LLM interpretation capabilities in NITRA.

Scope includes any advisory interpretation domain (for example liquidity-driven market-structure interpretation).

This LLD standardizes the required seven artifacts:

1. Framework ontology
2. Rulebook with precedence and edge cases
3. Structured scenario dataset
4. Output JSON schema
5. RAG document taxonomy
6. Evaluation benchmark
7. Prompt contract for inference

## 2. Design Constraints

- Deterministic execution/risk remains authoritative.
- LLM outputs are advisory only.
- Every interpretation output must be schema-validated.
- Artifacts are versioned, testable, and promotion-gated.

## 3. Artifact 1 — Framework Ontology

### 3.1 Objective
Define canonical concepts and relations used by interpretation logic.

### 3.2 Minimum ontology entities
- `liquidity_pool`
- `liquidity_taken_event`
- `directional_objective`
- `reference_candle`
- `pullback`
- `minor_structure_pair`
- `major_structure_pair`
- `timeframe_projection`
- `fractal_footprint`

### 3.3 Minimum relation set
- `targets`
- `invalidates`
- `extends`
- `terminates`
- `breaks_structural_high`
- `is_higher_timeframe_footprint_of`

### 3.4 Contract fields
- `ontology_version`
- `entity_definitions[]`
- `relation_definitions[]`
- `forbidden_inferences[]`

### 3.5 Canonical baseline binding

For liquidity-structure interpretation, the ontology baseline is mandatory:
- `docs/design/ontology/liquidity-driven-market-structure-ontology.md`

Any deviation must declare explicit versioned variance and benchmark compatibility evidence.

## 4. Artifact 2 — Rulebook (Precedence + Edge Cases)

### 4.1 Objective
Encode deterministic interpretation rules and conflict resolution order.

### 4.2 Rule classes
- Bias rules
- Pullback initiation/termination rules
- Extension rules
- Inside/outside bar rules
- Minor/major activation rules

### 4.3 Precedence contract
- Explicit ordered precedence list required.
- Later rules cannot override higher-priority safety/conflict rules.

### 4.4 Edge-case registry (minimum)
- equal-low inside bar
- outside bar with/without extension
- wick-only break vs body break
- sparse/partial candle stream
- ambiguous dual-break in same aggregation window

### 4.5 Contract fields
- `rulebook_version`
- `rules[]` with `id`, `priority`, `condition`, `action`
- `edge_cases[]`
- `conflict_resolution_policy`

## 5. Artifact 3 — Structured Scenario Dataset

### 5.1 Objective
Provide reproducible scenario inputs and expected interpretation outputs.

### 5.2 Scenario unit shape
- `scenario_id`
- `domain`
- `input_stream_ref` (bars/ticks snapshot)
- `expected_output_ref`
- `tags` (inside-bar, extension, major-break, etc.)
- `difficulty` and `coverage_bucket`

### 5.3 Dataset requirements
- golden deterministic set
- adversarial/edge-case set
- regression carry-forward set

### 5.4 Contract fields
- `dataset_version`
- `scenario_count`
- `coverage_matrix`
- `label_quality_notes`

## 6. Artifact 4 — Output JSON Schema

### 6.1 Objective
Enforce machine-validated interpretation outputs.

### 6.2 Minimum output sections
- metadata (`schema_version`, `model_id`, `prompt_contract_version`)
- bias assessment
- active pullback state
- minor structure archive
- major structure archive
- uncertainty and evidence references

### 6.3 Validation policy
- unknown fields disallowed in strict mode
- required fields must be present
- enum-constrained labels for state and events

### 6.4 Failure mode
Schema validation failure must fail closed at advisory boundary.

## 7. Artifact 5 — RAG Document Taxonomy

### 7.1 Objective
Control retrieval scope and prevent ungoverned context mixing.

### 7.2 Required taxonomy classes
- ontology docs
- rulebook docs
- scenario exemplars
- operational constraints
- disallowed sources

### 7.3 Retrieval policy
- class allowlist by task type
- freshness/priority policy
- citation requirement per response

### 7.4 Contract fields
- `taxonomy_version`
- `document_classes[]`
- `retrieval_policies[]`
- `blocklist_policies[]`

## 8. Artifact 6 — Evaluation Benchmark

### 8.1 Objective
Define measurable promotion gates for interpretation quality and safety.

### 8.2 Required benchmark dimensions
- structural accuracy (minor/major/pullback labels)
- precedence consistency (rule conflict handling)
- schema compliance rate
- edge-case pass rate
- stability under replay/regression

### 8.3 Gate examples
- `schema_compliance = 100%`
- `edge_case_pass_rate >= threshold`
- `major_structure_precision >= threshold`
- `no critical conflict-resolution violations`

### 8.4 Contract fields
- `benchmark_version`
- `metrics[]`
- `thresholds[]`
- `promotion_gate_status`

## 9. Artifact 7 — Prompt Contract for Inference

### 9.1 Objective
Bind prompt behavior to ontology/rulebook/schema/taxonomy contracts.

### 9.2 Contract composition
- system constraints
- allowed reasoning pattern
- mandatory output format (JSON-only where required)
- citation policy to retrieved classes
- refusal/fallback behavior when evidence is insufficient

### 9.3 Versioning
Prompt contract must carry:
- `prompt_contract_version`
- linked versions of ontology/rulebook/schema/taxonomy/benchmark

### 9.4 Runtime checks
- pre-inference: contract compatibility check
- post-inference: schema validation + benchmark sampling hooks

## 10. SDLC Integration

### 10.1 Required build/test gates
- artifact presence check (all seven)
- schema validation tests
- scenario benchmark run
- prompt-contract compatibility tests

### 10.2 Release promotion rules
Promotion is blocked if any of the following is true:
- missing artifact
- version mismatch across linked contracts
- benchmark gate failure
- schema compliance below required threshold

## 11. Repository Placement Recommendation

Suggested structure:

- `docs/design/nitra_system_lld/10_interpretation_governance_artifacts.md`
- `contracts/ai/ontology/`
- `contracts/ai/rulebook/`
- `contracts/ai/scenarios/`
- `contracts/ai/output-schema/`
- `contracts/ai/rag-taxonomy/`
- `contracts/ai/benchmarks/`
- `contracts/ai/prompt-contracts/`

## 12. Compliance Checklist

- [ ] Ontology exists and is versioned.
- [ ] Rulebook defines precedence + edge cases.
- [ ] Scenario dataset covers golden + adversarial + regression sets.
- [ ] Output JSON schema is strict and validated.
- [ ] RAG taxonomy and retrieval policy are defined.
- [ ] Benchmark thresholds are explicit and pass.
- [ ] Prompt contract is versioned and linked to all dependent artifacts.
