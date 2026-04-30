# Deterministic-First Execution Dependency Map (P0 -> P8)

## Purpose

Define the strict dependency order for Section 5 completion so execution stays deterministic-first and avoids premature ML/LLM scope.

## Global Rules

1. No ticket in a higher priority may start before all blocking tickets in lower priorities are complete.
2. Each component ticket must close with its required control-panel companion ticket.
3. P2+ is blocked until P0 and P1 closure gates pass.
4. LLM/RAG work remains advisory-only and last-priority.

## Priority Graph

```text
P0 -> P1 -> P2 -> P3 -> P4 -> P5 -> P6 -> P7 -> P8
```

### P0: Non-Negotiable Core (Data Acquisition)

Execution order:

1. `DEV-00065` governance map and closure contract
2. Feeds core reliability:
   - `DEV-00068`, `DEV-00069`, `DEV-00070`, `DEV-00141`, `DEV-00142`, `DEV-00143`
3. Raw data lake foundation:
   - `DEV-00071`, `DEV-00072`, `DEV-00073`
4. Kafka backbone hardening:
   - `DEV-00074`, `DEV-00075`, `DEV-00076`
5. Control panel companions:
   - `DEV-00124`, `DEV-00125`, `DEV-00126`

Exit dependency:

- P1 cannot start before all above are complete.

### P1: Deterministic Market Data Foundation

Execution order:

1. Normalization/replay integrity:
   - `DEV-00077`, `DEV-00078`, `DEV-00079`, `DEV-00144`, `DEV-00145`
2. Time-series storage hardening:
   - `DEV-00083`, `DEV-00084`, `DEV-00085`
3. Structure determinism:
   - `DEV-00080`, `DEV-00081`, `DEV-00082`, `DEV-00146`
4. Control panel companions:
   - `DEV-00127`, `DEV-00129`, `DEV-00128`

Exit dependency:

- P2 cannot start before all above are complete.

### P2: Research and Validation

Execution order:

1. `DEV-00091`, `DEV-00092`, `DEV-00093`, `DEV-00094`, `DEV-00147`
2. Control panel companion: `DEV-00131`

### P3: Decision Layer

Execution order:

1. Feature platform: `DEV-00086..DEV-00090`
2. Online inference: `DEV-00096..DEV-00099`
3. Control panel companions: `DEV-00130`, `DEV-00132`

### P4: Trading Control Plane

Execution order:

1. `DEV-00100`, `DEV-00101`, `DEV-00102`, `DEV-00148`
2. Control panel companion: `DEV-00133`

### P5: Execution

Execution order:

1. `DEV-00103`, `DEV-00104`, `DEV-00105`
2. Control panel companion: `DEV-00134`

### P6: Observability and Intelligence Foundation

Execution order:

1. `DEV-00112`, `DEV-00113`, `DEV-00114`, `DEV-00115`
2. Control panel companion: `DEV-00136`

### P7: MLflow and Feature Maturity

Execution order:

1. `DEV-00095`

### P8: RAG + LLM Analyst (Advisory-Only)

Execution order:

1. `DEV-00106`, `DEV-00107`, `DEV-00108`, `DEV-00109`, `DEV-00110`, `DEV-00111`
2. Control panel companion: `DEV-00135`

## Cross-Cutting Stream

The following run in controlled parallel but must not break priority-gate ordering:

- `DEV-00066` traceability matrix
- `DEV-00116`, `DEV-00117`, `DEV-00118` platform topology
- `DEV-00119`, `DEV-00120`, `DEV-00121` security controls
- `DEV-00137`, `DEV-00138`, `DEV-00151`, `DEV-00152` control-panel platform/security/config foundations

## Finalization Dependencies

- `DEV-00067` readiness gate aggregator requires all priority and cross-cutting scopes complete.
- `DEV-00140` requires all control-panel module scopes complete.
- `DEV-00122` closes only when all Section 5 contracts are evidenced end-to-end.
