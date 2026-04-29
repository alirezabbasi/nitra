#!/usr/bin/env python3
"""Deterministic feature-service baseline (DEV-00038).

This baseline intentionally keeps runtime logic deterministic and point-in-time safe:
- only current structure snapshot + prior persisted state are used,
- no future bars or lookahead joins are allowed,
- feature lineage is persisted for every emitted snapshot.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class FeatureKey:
    venue: str
    canonical_symbol: str
    timeframe: str


@dataclass
class FeatureState:
    last_bucket_start: datetime
    last_close: float
    ewma_return: float


@dataclass(frozen=True)
class ParsedStructure:
    key: FeatureKey
    bucket_start: datetime
    last_event_ts: datetime
    bar_open: float
    bar_high: float
    bar_low: float
    bar_close: float
    trend: str
    phase: str
    objective: str
    transition_reason: str


FEATURE_SCHEMA_VERSION = 1
FEATURE_SET_VERSION = "dev-00038.v1"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_ts(raw: str) -> datetime:
    value = raw.replace("Z", "+00:00")
    return datetime.fromisoformat(value).astimezone(timezone.utc)


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def parse_structure_payload(payload: Dict[str, Any]) -> Optional[ParsedStructure]:
    try:
        venue = str(payload["venue"]).strip().lower()
        symbol = str(payload["canonical_symbol"]).strip().upper()
        timeframe = str(payload.get("timeframe", "1m")).strip()
        bucket_start = parse_ts(str(payload["bucket_start"]))
        last_event_ts = parse_ts(str(payload.get("last_event_ts", payload["bucket_start"])))
        input_bar = payload["input_bar"]
        state = payload["state"]

        bar_open = float(input_bar["open"])
        bar_high = float(input_bar["high"])
        bar_low = float(input_bar["low"])
        bar_close = float(input_bar["close"])

        trend = str(state.get("trend", "neutral"))
        phase = str(state.get("phase", "init"))
        objective = str(state.get("objective", "none"))
        transition_reason = str(payload.get("transition_reason", state.get("last_transition_reason", "unknown")))
    except (KeyError, TypeError, ValueError):
        return None

    if not venue or not symbol:
        return None
    if bar_high < bar_low:
        return None

    return ParsedStructure(
        key=FeatureKey(venue=venue, canonical_symbol=symbol, timeframe=timeframe),
        bucket_start=bucket_start,
        last_event_ts=last_event_ts,
        bar_open=bar_open,
        bar_high=bar_high,
        bar_low=bar_low,
        bar_close=bar_close,
        trend=trend,
        phase=phase,
        objective=objective,
        transition_reason=transition_reason,
    )


def compute_feature_vector(parsed: ParsedStructure, previous: Optional[FeatureState]) -> Dict[str, float | str]:
    """Compute deterministic features from PIT-safe inputs only.

    No lookahead guarantee:
    - current structure snapshot payload,
    - previous persisted feature state (older bucket only).
    """
    prev_close = previous.last_close if previous else parsed.bar_open
    prev_close = prev_close if prev_close > 0 else parsed.bar_open

    ret_1 = (parsed.bar_close - prev_close) / prev_close if prev_close else 0.0
    bar_range = max(parsed.bar_high - parsed.bar_low, 0.0)
    bar_body = parsed.bar_close - parsed.bar_open
    range_body_ratio = (abs(bar_body) / bar_range) if bar_range > 0 else 0.0

    prev_ewma = previous.ewma_return if previous else 0.0
    ewma_return = 0.2 * ret_1 + 0.8 * prev_ewma

    trend_score = 0.0
    if parsed.trend == "bullish":
        trend_score = 1.0
    elif parsed.trend == "bearish":
        trend_score = -1.0

    phase_pullback = 1.0 if parsed.phase == "pullback" else 0.0

    return {
        "ret_1": round(ret_1, 12),
        "bar_range": round(bar_range, 12),
        "bar_body": round(bar_body, 12),
        "range_body_ratio": round(clamp(range_body_ratio, 0.0, 1.0), 12),
        "ewma_return": round(ewma_return, 12),
        "trend_score": trend_score,
        "phase_pullback": phase_pullback,
        "transition_reason": parsed.transition_reason,
    }


def next_feature_state(parsed: ParsedStructure, vector: Dict[str, float | str]) -> FeatureState:
    return FeatureState(
        last_bucket_start=parsed.bucket_start,
        last_close=parsed.bar_close,
        ewma_return=float(vector["ewma_return"]),
    )


def build_feature_payload(
    parsed: ParsedStructure,
    vector: Dict[str, float | str],
    source_topic: str,
    source_partition: int,
    source_offset: int,
) -> Dict[str, Any]:
    return {
        "venue": parsed.key.venue,
        "canonical_symbol": parsed.key.canonical_symbol,
        "timeframe": parsed.key.timeframe,
        "event_ts": parsed.last_event_ts.isoformat(),
        "bucket_start": parsed.bucket_start.isoformat(),
        "feature_set_version": FEATURE_SET_VERSION,
        "features": vector,
        "lineage": {
            "source_topic": source_topic,
            "source_partition": source_partition,
            "source_offset": source_offset,
            "window": {
                "previous_bucket_start": None,
                "current_bucket_start": parsed.bucket_start.isoformat(),
            },
            "schema_version": FEATURE_SCHEMA_VERSION,
        },
    }


def build_envelope(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "message_id": str(uuid.uuid4()),
        "emitted_at": utc_now_iso(),
        "schema_version": FEATURE_SCHEMA_VERSION,
        "headers": {},
        "payload": payload,
        "retry": None,
    }


def compare_online_offline_features(online: Dict[str, float | str], offline: Dict[str, float | str], tol: float = 1e-12) -> Tuple[bool, str]:
    for key, online_value in online.items():
        if key not in offline:
            return False, f"missing_key:{key}"
        offline_value = offline[key]
        if isinstance(online_value, float):
            if abs(float(online_value) - float(offline_value)) > tol:
                return False, f"float_mismatch:{key}"
        else:
            if online_value != offline_value:
                return False, f"value_mismatch:{key}"
    return True, "ok"


def main() -> int:
    # Runtime shell intentionally lightweight for baseline ticket.
    # Real transport wiring can evolve without changing deterministic feature contract.
    input_topic = os.getenv("FEATURE_INPUT_TOPIC", "structure.snapshot.v1")
    output_topic = os.getenv("FEATURE_OUTPUT_TOPIC", "features.snapshot.v1")
    print(
        json.dumps(
            {
                "service": "feature-service",
                "status": "baseline_ready",
                "input_topic": input_topic,
                "output_topic": output_topic,
                "feature_set_version": FEATURE_SET_VERSION,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
