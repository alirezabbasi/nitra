# Liquidity-Driven Market Structure Ontology (Canonical Baseline)

Status: normative  
Scope: project-wide interpretation baseline for liquidity-structure analysis  
Applies to: chart layer semantics, rulebooks, scenario labeling, schema outputs, RAG retrieval, benchmarking, and prompt contracts

## 1. Core Market Principles

- Market is modeled as a continuous price stream driven by liquidity interaction.
- Price is interpreted as movement between Liquidity Points, not intrinsic “trend”.
- Timeframes (`1m`, `5m`, `15m`, `1h`, etc.) are sampling windows over a continuous stream.
- Candle visuals are compressed artifacts and may hide internal sequence events.
- Structural interpretation MUST prioritize liquidity interaction logic over candle-shape heuristics.

## 2. Directional Bias from Liquidity State

- Bias is defined by taken liquidity versus remaining opposing liquidity.
- If upper liquidity is taken and lower opposing liquidity remains, directional objective is bearish until lower liquidity is reached.
- Inverse logic applies for bullish objective.
- For implementation, "taken" means a confirmed breach of the corresponding prior liquidity point in sequence context.

## 3. Pullback Mechanics (Bearish reference model)

### 3.1 Reference Candle
- The reference candle is the latest candle before pullback initiation.
- It anchors pullback start/termination conditions.

### 3.2 Pullback Start
- Condition:
  - `B.high > A.high`
  - `A.low` not broken

### 3.3 Pullback Termination
- Pullback terminates when the active reference low is broken (wick or body).

## 4. Pullback Extension

- Pullback remains active while:
  - active reference low remains intact
- Pullback does not require continuous higher-high printing to remain active.

## 5. Special Candle Conditions

### 5.1 Inside Bar
- Inside bar condition:
  - `B.high <= A.high`
  - `B.low >= A.low`
- Default behavior: ignore structurally.
- Equal-low exception:
  - if `B.low == reference_low`, shift reference from `A` to `B`.
  - new start trigger: break of `B.high`
  - new termination trigger: break of `B.low`

### 5.2 Outside Bar
- Outside bar condition:
  - `B.high > A.high`
  - `B.low < A.low`
- Pullback is initiated.
- Termination reference resolution:
  - if next candle `C.high > B.high`: extension confirmed, termination reference shifts to `B` (terminate on `B.low` break)
  - else: termination reference remains `A` (terminate on `A.low` break)

## 5.3 Bullish Inverse Mapping

- Sections 3-5 define the bearish reference model.
- Bullish evaluation is the strict inverse:
  - swap `high` and `low` logic symmetrically,
  - swap upper/lower liquidity interpretation,
  - preserve identical precedence rules (inside/outside/reference/termination).

## 6. Minor Structure

- Every completed pullback yields one minor pair:
  - Minor Low: lowest price immediately before pullback start (typically reference low)
  - Minor High: highest price reached during pullback before termination
- Minor pullbacks are evaluated independently at each eligible sequence and MUST be recorded even when they occur inside an active pullback or inside a major pullback context.
- Minor structure archive is append-only.
- Prior pairs are never discarded; only active pair changes.

## 7. Major Structure Activation

- Major activation occurs when pullback high breaks archived structural highs:
  - previous minor highs
  - previous major highs
- Condition: `pullback.high > any archived structural high`

## 8. Major High

- Major High is the maximum price reached by the pullback that caused structural break (not the broken prior high).

## 9. Major Low

- Major Low is the lowest price immediately before the pullback that formed the major high.

## 10. Major Structural Pair

- Major pair is always:
  - Major Low
  - Major High

## 11. Continuous Market Principle

- No natural time boundaries exist in raw price process.
- Timeframe boundaries are observational artifacts.
- Interpretation must model sequence and liquidity interaction, not candle abstractions alone.

## 12. Fractal Observation Contract

- Higher timeframe structure is compressed lower-timeframe behavior.
- Large structures are emergent aggregates of smaller structures.
- Interpretation layers must support nested/fractal mapping.

## 13. Major Structure as Higher-Timeframe Footprint

- Minor structure: local fluctuation in current observational scale.
- Major structure: expansion footprint of higher-order behavior within same chart stream.

## 14. Analytical Implication

- Analysts can infer larger structural influence without mandatory timeframe switching.
- Major pairs mark where higher-order dynamics became visible in local stream.

## 15. Project Enforcement

This ontology is a mandatory base contract for:
- chart liquidity layer semantics,
- interpretation rulebooks and edge-case precedence,
- scenario dataset labels,
- output schema fields/enums,
- RAG taxonomy classes for interpretation retrieval,
- benchmark metrics for structural correctness,
- prompt contract constraints.

Any interpretation component that diverges MUST declare explicit versioned variance and pass benchmark compatibility checks before promotion.

## 16. Liquidity Layer Execution Contract

- Liquidity layer projection window is `today + yesterday`, extended up to the current active candle.
- Closed-candle structure must remain deterministic; active-candle extension may be provisional.
- Chart must distinguish completed versus active (in-progress) structure state in overlay semantics.
