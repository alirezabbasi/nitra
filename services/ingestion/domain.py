import json
from datetime import datetime, timezone


def parse_ts(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def minute_bucket(ts: datetime) -> datetime:
    return ts.replace(second=0, microsecond=0, tzinfo=timezone.utc)


def canonical_symbol(broker_symbol: str) -> str:
    return broker_symbol.replace("_", "").replace("-", "").replace(".", "").upper()


def classify_market_payload(payload: dict) -> str:
    if payload.get("bid") is not None or payload.get("ask") is not None:
        return "raw_tick"
    if payload.get("price") is not None and payload.get("size") is not None:
        return "trade_print"
    if payload.get("best_bid") is not None or payload.get("best_ask") is not None:
        return "book_event"
    return "raw_tick"


def load_symbol_registry(path: str) -> dict[tuple[str, str], str]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    mapping: dict[tuple[str, str], str] = {}
    for row in data.get("mappings", []):
        key = (str(row.get("venue", "")).lower(), str(row.get("broker_symbol", "")))
        value = str(row.get("canonical_symbol", ""))
        if key[0] and key[1] and value:
            mapping[key] = value
    return mapping
