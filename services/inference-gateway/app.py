#!/usr/bin/env python3
"""Deterministic signal scorer baseline (DEV-00039).

This module converts feature snapshots into reproducible signal decisions with
explicit explainability metadata and strict config/version pinning.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


SCORER_CONFIG_VERSION = os.getenv("SIGNAL_SCORER_CONFIG_VERSION", "dev-00039.v1")
SCORER_MODEL_VERSION = os.getenv("SIGNAL_MODEL_VERSION", "deterministic-linear-v1")
SCORE_THRESHOLD_BUY = float(os.getenv("SIGNAL_SCORE_THRESHOLD_BUY", "0.62"))
SCORE_THRESHOLD_SELL = float(os.getenv("SIGNAL_SCORE_THRESHOLD_SELL", "-0.62"))
CONFIDENCE_CAP = float(os.getenv("SIGNAL_CONFIDENCE_CAP", "0.99"))


@dataclass(frozen=True)
class FeatureInput:
    venue: str
    canonical_symbol: str
    timeframe: str
    event_ts: datetime
    bucket_start: datetime
    features: Dict[str, float | str]
    feature_set_version: str
    lineage: Dict[str, Any]


@dataclass(frozen=True)
class SignalDecision:
    side: str
    score: float
    confidence: float
    notional_requested: float
    reason_codes: List[str]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_ts(raw: str) -> datetime:
    return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def parse_feature_payload(payload: Dict[str, Any]) -> Optional[FeatureInput]:
    try:
        venue = str(payload["venue"]).strip().lower()
        symbol = str(payload["canonical_symbol"]).strip().upper()
        timeframe = str(payload.get("timeframe", "1m")).strip()
        event_ts = parse_ts(str(payload["event_ts"]))
        bucket_start = parse_ts(str(payload.get("bucket_start", payload["event_ts"])))
        features = dict(payload["features"])
        feature_set_version = str(payload["feature_set_version"])
        lineage = dict(payload["lineage"])
    except (KeyError, TypeError, ValueError):
        return None

    if not venue or not symbol:
        return None

    return FeatureInput(
        venue=venue,
        canonical_symbol=symbol,
        timeframe=timeframe,
        event_ts=event_ts,
        bucket_start=bucket_start,
        features=features,
        feature_set_version=feature_set_version,
        lineage=lineage,
    )


def deterministic_score(features: Dict[str, float | str]) -> Tuple[float, List[str]]:
    """Deterministic linear scorer with explainability reason codes."""
    ret_1 = float(features.get("ret_1", 0.0))
    ewma = float(features.get("ewma_return", 0.0))
    trend_score = float(features.get("trend_score", 0.0))
    pullback = float(features.get("phase_pullback", 0.0))
    body_ratio = float(features.get("range_body_ratio", 0.0))

    score = (
        0.45 * ret_1 +
        0.30 * ewma +
        0.35 * trend_score -
        0.25 * pullback +
        0.10 * (body_ratio - 0.5)
    )
    score = round(clamp(score, -1.0, 1.0), 12)

    reasons: List[str] = []
    if trend_score > 0:
        reasons.append("trend_bullish")
    elif trend_score < 0:
        reasons.append("trend_bearish")
    else:
        reasons.append("trend_neutral")

    if ewma > 0:
        reasons.append("momentum_positive")
    elif ewma < 0:
        reasons.append("momentum_negative")

    if pullback > 0:
        reasons.append("pullback_active")

    if body_ratio >= 0.65:
        reasons.append("body_strength_high")

    return score, reasons


def decide_signal(score: float, reasons: List[str]) -> SignalDecision:
    if score >= SCORE_THRESHOLD_BUY:
        side = "buy"
    elif score <= SCORE_THRESHOLD_SELL:
        side = "sell"
    else:
        side = "hold"

    confidence = round(clamp(abs(score), 0.0, CONFIDENCE_CAP), 12)
    notional_requested = 1000.0 if side != "hold" else 0.0

    final_reasons = list(reasons)
    final_reasons.append(f"threshold_buy={SCORE_THRESHOLD_BUY}")
    final_reasons.append(f"threshold_sell={SCORE_THRESHOLD_SELL}")
    final_reasons.append(f"decision_side={side}")

    return SignalDecision(
        side=side,
        score=score,
        confidence=confidence,
        notional_requested=notional_requested,
        reason_codes=final_reasons,
    )


def build_signal_payload(feature: FeatureInput, decision: SignalDecision) -> Dict[str, Any]:
    return {
        "venue": feature.venue,
        "canonical_symbol": feature.canonical_symbol,
        "timeframe": feature.timeframe,
        "event_ts": feature.event_ts.isoformat(),
        "bucket_start": feature.bucket_start.isoformat(),
        "signal": {
            "side": decision.side,
            "score": decision.score,
            "confidence": decision.confidence,
            "notional_requested": decision.notional_requested,
            "reason_codes": decision.reason_codes,
            "scorer": {
                "config_version": SCORER_CONFIG_VERSION,
                "model_version": SCORER_MODEL_VERSION,
                "feature_set_version": feature.feature_set_version,
            },
            "feature_refs": {
                "lineage": feature.lineage,
                "keys": sorted(feature.features.keys()),
            },
        },
    }


def build_envelope(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "message_id": str(uuid.uuid4()),
        "emitted_at": utc_now_iso(),
        "schema_version": 1,
        "headers": {},
        "payload": payload,
        "retry": None,
    }


def run_calibration(samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    decisions = []
    buy_count = sell_count = hold_count = 0
    scores: List[float] = []

    for raw in samples:
        parsed = parse_feature_payload(raw)
        if not parsed:
            continue
        score, reasons = deterministic_score(parsed.features)
        decision = decide_signal(score, reasons)
        decisions.append(decision)
        scores.append(score)
        if decision.side == "buy":
            buy_count += 1
        elif decision.side == "sell":
            sell_count += 1
        else:
            hold_count += 1

    n = len(scores)
    avg_score = round(sum(scores) / n, 12) if n else 0.0
    return {
        "samples": n,
        "avg_score": avg_score,
        "buy": buy_count,
        "sell": sell_count,
        "hold": hold_count,
        "config_version": SCORER_CONFIG_VERSION,
        "model_version": SCORER_MODEL_VERSION,
        "status": "ok" if n else "empty",
    }


def main() -> int:
    print(
        json.dumps(
            {
                "service": "signal-engine",
                "status": "baseline_ready",
                "input_topic": os.getenv("SIGNAL_INPUT_TOPIC", "features.snapshot.v1"),
                "output_topic": os.getenv("SIGNAL_OUTPUT_TOPIC", "decision.signal_scored.v1"),
                "config_version": SCORER_CONFIG_VERSION,
                "model_version": SCORER_MODEL_VERSION,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
