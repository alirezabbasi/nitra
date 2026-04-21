# Rust Codebase Skeleton (End-to-End)

This is the canonical map of where code lives and where behavior is implemented.

## 1. Workspace Layout

- Root `Cargo.toml` defines a Rust workspace.
- Shared crates:
  - `crates/domain`: canonical market-domain models (`CanonicalEvent`, `Bar`, etc.)
  - `crates/contracts`: stream contracts, envelopes, topic definitions, execution/gap/replay events
- Service crates:
  - `services/connector`
  - `services/normalizer`
  - `services/bar_engine`
  - `services/gap_engine`
  - `services/backfill_worker`
  - `services/archive_worker`
  - `services/cold_loader`
  - `services/risk_gateway`
  - `services/oms`
- `services/query_api`
- `services/chart_ui` (static web chart service)

## 2. Shared Core Types (Cross-Service)

Primary files:

- `crates/domain/src/lib.rs`
- `crates/contracts/src/lib.rs`

Key role:

- `domain` holds canonical market objects and enums.
- `contracts` holds inter-service message payloads, topic constants, and retry/replay metadata.

If you are looking for "where the schema is defined", start in these two files.

## 3. Service Entry Points and Main Responsibilities

All services start in `services/<name>/src/main.rs`.

### Ingestion and Market Data Pipeline

- `connector`:
  - Entry: `services/connector/src/main.rs`
  - Core functions: `run_connector`, `run_oanda_adapter_session`, `run_capital_adapter_session`, `run_coinbase_adapter_session`, `publish_raw_event`
  - Responsibility: broker adapter sessions -> publish raw events to `raw.market.<venue>`

- `normalizer`:
  - Entry: `services/normalizer/src/main.rs`
  - Core functions: `run_once`, `normalize_raw_envelope`, `persist_market_entity_if_supported`, `classify_market_entity`
  - Responsibility: raw topic consume -> canonical normalization -> persist entity tables -> publish normalized events

- `bar_engine`:
  - Entry: `services/bar_engine/src/main.rs`
  - Core functions: `run_once`, `process_event`, `persist_and_publish_bar`
  - Responsibility: aggregate normalized events into bars (`ohlcv_bar`) and publish `bar.1m`

- `gap_engine`:
  - Entry: `services/gap_engine/src/main.rs`
  - Core functions: `run_once`, `process_bar`, `find_missing_ranges`, `insert_and_maybe_emit_gap`
  - Responsibility: detect missing bar windows and emit `gap.events`

- `backfill_worker`:
  - Entry: `services/backfill_worker/src/main.rs`
  - Core functions: `run_once`, `process_gap`, `split_gap_into_chunks`, lock helpers
  - Responsibility: consume gap events and schedule replay/backfill jobs

- `archive_worker`:
  - Entry: `services/archive_worker/src/main.rs`
  - Core functions: `run_once`, `write_parquet`, `build_object_key`, `sha256_of_file`
  - Responsibility: snapshot hot bars into Parquet archive + manifest/checkpoint tracking

- `cold_loader`:
  - Entry: `services/cold_loader/src/main.rs`
  - Core functions: `run_once`, `read_archive_parquet`, `insert_bars`, `mark_manifest_loaded`
  - Responsibility: load archived Parquet into ClickHouse for cold analytics

### Execution and Risk Path

- `risk_gateway`:
  - Entry: `services/risk_gateway/src/main.rs`
  - Core functions: `run_once`, `evaluate_pre_trade`, `evaluate_and_persist_decision`, `publish_decision`
  - Responsibility: consume execution intents, apply deterministic risk policy, publish risk decisions

- `oms`:
  - Entry: `services/oms/src/main.rs`
  - Core functions: `run_once`, `process_risk_decision`, `submit_order_if_new`, `process_fill`, `reconcile_open_orders`
  - Responsibility: order lifecycle state machine + reconciliation + fill handling

### Query/Read Path

- `query_api`:
  - Entry: `services/query_api/src/main.rs`
  - Core handlers: `health`, `bars_hot`, `bars_cold`
  - Responsibility: HTTP read API from TimescaleDB (hot) and ClickHouse (cold)

## 4. Web Services and Routes

### Public query API (`query_api`)

File: `services/query_api/src/main.rs`

Routes:

- `GET /health`
- `GET /v1/bars/hot`
- `GET /v1/bars/cold`
- `GET /v1/ticks/hot`

### Chart web service (`chart-ui`)

Files:

- `services/chart_ui/nginx.conf`
- `services/chart_ui/www/index.html`

Routes:

- `GET /` -> chart web UI
- `GET /api/*` -> reverse-proxy pass-through to `query-api`

Runtime behavior notes:

- Chart area is viewport-filling below controls on desktop/mobile layouts.
- In hot mode, chart UI polls `/api/v1/ticks/hot` and synthesizes a live (provisional) minute candle from tick data.

### Internal observability endpoints (`risk_gateway`, `oms`)

Files:

- `services/risk_gateway/src/main.rs`
- `services/oms/src/main.rs`

Routes in both:

- `GET /health`
- `GET /ready`
- `GET /metrics`

These are operational endpoints, not business/public API equivalents.

## 5. Common Service Skeleton Pattern

Most services follow this shape:

1. `*Config::from_env()` builds runtime config.
2. `main()` starts retry loop.
3. `run_once()` opens Kafka consumer/producer and DB connection.
4. message handling function parses payload and applies business logic.
5. idempotency helper (`processed_message_ledger`) prevents duplicate side effects.
6. commit Kafka offsets only after successful side effects.

This is the core deterministic behavior pattern across the repo.

## 6. Infra and Runtime Wiring

- `docker-compose.yml` wires all services, env vars, startup order.
- `infra/docker/rust-services.Dockerfile` builds all Rust binaries with shared cache.
- `infra/redpanda/topics.csv` defines topic bootstrap list.
- `infra/timescaledb/init/*.sql` defines hot-store schema and migrations.
- `infra/symbols/registry.v1.json` maps broker symbols to canonical symbols.

## 7. Tests and Validation Structure

- Unit tests are mostly inside each service `src/main.rs` under `#[cfg(test)]`.
- Step/epic validation is in `tests/epic-xx/run.sh`.
- Root test orchestrator:
  - `tests/run-all.sh`
- Common commands:
  - `make test`
  - `make test-epic-21` (example epic-specific pack)

## 8. FastAPI Developer Quick Mapping

- "Where are routers?" -> `query_api` (`axum::Router`) and obs endpoints in `risk_gateway`/`oms`.
- "Where are request/response models?" -> `crates/contracts` and `crates/domain`.
- "Where is business logic?" -> service `run_once`/processing functions in each `services/*/src/main.rs`.
- "Where is db schema?" -> `infra/timescaledb/init/*.sql` (and ClickHouse init under `infra/clickhouse/` when present).
- "Where are async background jobs?" -> all worker services listed above.

## 9. FastAPI Equivalence Cheat Sheet

This section maps common FastAPI building blocks to Rust (`axum`) with concrete code examples.

### 9.1 APIRouter -> axum Router

FastAPI:

```python
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/v1/orders", tags=["orders"])

class OrderOut(BaseModel):
    id: str
    symbol: str
    qty: float

@router.get("/{order_id}", response_model=OrderOut)
async def get_order(order_id: str):
    return OrderOut(id=order_id, symbol="BTC-USDT", qty=0.5)
```

Rust (`axum`):

```rust
use axum::{extract::Path, routing::get, Json, Router};
use serde::Serialize;

#[derive(Serialize)]
struct OrderOut {
    id: String,
    symbol: String,
    qty: f64,
}

async fn get_order(Path(order_id): Path<String>) -> Json<OrderOut> {
    Json(OrderOut {
        id: order_id,
        symbol: "BTC-USDT".to_string(),
        qty: 0.5,
    })
}

fn orders_router() -> Router {
    Router::new()
        .route("/:order_id", get(get_order))
}

fn app() -> Router {
    Router::new()
        .nest("/v1/orders", orders_router())
}
```

### 9.2 Depends(...) DI -> State + explicit wiring

FastAPI:

```python
from fastapi import Depends, FastAPI

app = FastAPI()

class Repo:
    async def list_symbols(self) -> list[str]:
        return ["BTC-USDT", "ETH-USDT"]

def get_repo() -> Repo:
    return Repo()

@app.get("/v1/symbols")
async def symbols(repo: Repo = Depends(get_repo)):
    return await repo.list_symbols()
```

Rust (`axum`):

```rust
use axum::{extract::State, routing::get, Json, Router};
use std::sync::Arc;

#[derive(Clone)]
struct Repo;

impl Repo {
    async fn list_symbols(&self) -> Vec<String> {
        vec!["BTC-USDT".into(), "ETH-USDT".into()]
    }
}

#[derive(Clone)]
struct AppState {
    repo: Arc<Repo>,
}

async fn symbols(State(state): State<AppState>) -> Json<Vec<String>> {
    Json(state.repo.list_symbols().await)
}

fn app() -> Router {
    let state = AppState { repo: Arc::new(Repo) };
    Router::new()
        .route("/v1/symbols", get(symbols))
        .with_state(state)
}
```

### 9.3 Pydantic model -> Rust struct (`serde`)

FastAPI:

```python
from pydantic import BaseModel, Field

class CreateOrderIn(BaseModel):
    symbol: str = Field(min_length=3)
    side: str
    qty: float

class CreateOrderOut(BaseModel):
    order_id: str
    status: str
```

Rust (`serde` + optional validation crate):

```rust
use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize)]
struct CreateOrderIn {
    symbol: String,
    side: String,
    qty: f64,
}

#[derive(Debug, Serialize)]
struct CreateOrderOut {
    order_id: String,
    status: String,
}
```

Handler using these models:

```rust
use axum::{Json, http::StatusCode};

async fn create_order(Json(input): Json<CreateOrderIn>) -> (StatusCode, Json<CreateOrderOut>) {
    // validation is explicit in Rust (manual checks or crate-based validators)
    if input.symbol.len() < 3 || input.qty <= 0.0 {
        return (
            StatusCode::BAD_REQUEST,
            Json(CreateOrderOut {
                order_id: String::new(),
                status: "invalid".to_string(),
            }),
        );
    }

    (
        StatusCode::CREATED,
        Json(CreateOrderOut {
            order_id: "ord_123".to_string(),
            status: "accepted".to_string(),
        }),
    )
}
```

### 9.4 Practical mapping for this repository

- FastAPI `APIRouter` modules map to service-level route builders in `services/query_api/src/main.rs`.
- FastAPI app dependencies (`Depends`) map to service config/state structs loaded from env and injected via `.with_state(...)`.
- Pydantic schemas map to shared Rust structs in `crates/contracts` and `crates/domain` when cross-service, or local structs when endpoint-local.
