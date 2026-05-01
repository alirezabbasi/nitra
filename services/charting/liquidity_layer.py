from __future__ import annotations

from datetime import datetime, timedelta, timezone
import statistics


def floor_to_tf(dt: datetime, tf_minutes: int) -> datetime:
    dt_utc = dt.astimezone(timezone.utc).replace(second=0, microsecond=0)
    minute = (dt_utc.minute // tf_minutes) * tf_minutes
    return dt_utc.replace(minute=minute)


def m5_window_bounds(now_utc: datetime) -> tuple[datetime, datetime, datetime]:
    current_bucket_start = floor_to_tf(now_utc, 5)
    last_closed_bucket_start = current_bucket_start - timedelta(minutes=5)
    start_of_today = now_utc.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_yesterday = start_of_today - timedelta(days=1)
    return start_of_yesterday, last_closed_bucket_start, current_bucket_start


def aggregate_m5_from_1m(rows: list[tuple], max_bucket_start: datetime) -> list[dict]:
    buckets: dict[datetime, dict] = {}
    for bucket_start, o, h, l, c, volume, trade_count in rows:
        if None in (bucket_start, o, h, l, c):
            continue
        if bucket_start > max_bucket_start:
            continue
        bucket_start_utc = bucket_start.astimezone(timezone.utc).replace(second=0, microsecond=0)
        m5_start = bucket_start_utc - timedelta(minutes=bucket_start_utc.minute % 5)
        if m5_start > max_bucket_start:
            continue
        group = buckets.get(m5_start)
        if group is None:
            buckets[m5_start] = {
                "timestamp": int(m5_start.timestamp() * 1000),
                "open": float(o),
                "high": float(h),
                "low": float(l),
                "close": float(c),
                "volume": float(volume or 0.0),
                "trade_count": int(trade_count or 0),
                "minute_count": 1,
            }
            continue
        group["high"] = max(group["high"], float(h))
        group["low"] = min(group["low"], float(l))
        group["close"] = float(c)
        group["volume"] += float(volume or 0.0)
        group["trade_count"] += int(trade_count or 0)
        group["minute_count"] += 1

    return [buckets[k] for k in sorted(buckets.keys())]


def _coalesce_price(mid: float | None, bid: float | None, ask: float | None, last: float | None) -> float | None:
    if mid is not None:
        return float(mid)
    if bid is not None and ask is not None:
        return float((bid + ask) / 2.0)
    if last is not None:
        return float(last)
    return None


def augment_current_m5_with_ticks(
    *,
    bars_5m: list[dict],
    ticks: list[tuple],
    current_bucket_start: datetime,
) -> list[dict]:
    current_bucket_ms = int(current_bucket_start.timestamp() * 1000)
    prices: list[float] = []
    for _ts, mid, bid, ask, last in ticks:
        price = _coalesce_price(mid, bid, ask, last)
        if price is not None:
            prices.append(price)

    if not prices:
        return bars_5m

    existing = bars_5m[-1] if bars_5m and int(bars_5m[-1]["timestamp"]) == current_bucket_ms else None
    if existing is not None:
        existing["high"] = max(float(existing["high"]), max(prices))
        existing["low"] = min(float(existing["low"]), min(prices))
        existing["close"] = float(prices[-1])
        existing["provisional"] = True
        return bars_5m

    open_price = float(prices[0])
    if bars_5m:
        open_price = float(bars_5m[-1]["close"])
    bars_5m.append(
        {
            "timestamp": current_bucket_ms,
            "open": open_price,
            "high": max(max(prices), open_price),
            "low": min(min(prices), open_price),
            "close": float(prices[-1]),
            "volume": 0.0,
            "trade_count": 0,
            "minute_count": 0,
            "provisional": True,
        }
    )
    return bars_5m


def _resolve_liquidity_bias(bars: list[dict]) -> str:
    if len(bars) < 2:
        return "bearish"
    upper_taken_idx = -1
    lower_taken_idx = -1
    for i in range(1, len(bars)):
        prev = bars[i - 1]
        cur = bars[i]
        if float(cur["high"]) > float(prev["high"]):
            upper_taken_idx = i
        if float(cur["low"]) < float(prev["low"]):
            lower_taken_idx = i

    if upper_taken_idx == -1 and lower_taken_idx == -1:
        return "bearish"
    if upper_taken_idx > lower_taken_idx:
        return "bearish"
    if lower_taken_idx > upper_taken_idx:
        return "bullish"
    return "bearish"


def _pairs_to_pivot_chain(pairs: list[dict], bars: list[dict]) -> list[dict]:
    valid: list[dict] = []
    for pair in pairs:
        low_idx = int(pair.get("low_idx", -1))
        high_idx = int(pair.get("high_idx", -1))
        if low_idx < 0 or high_idx < 0 or low_idx >= len(bars) or high_idx >= len(bars):
            continue
        valid.append(
            {
                "low_idx": low_idx,
                "high_idx": high_idx,
                "end_idx": int(pair.get("end_idx", high_idx)),
                "low_ts": int(bars[low_idx]["timestamp"]),
                "high_ts": int(bars[high_idx]["timestamp"]),
                "low_value": float(pair["low_value"]),
                "high_value": float(pair["high_value"]),
            }
        )

    # Ontology sequence fidelity: chain completed pullbacks in completion order.
    valid.sort(key=lambda p: (p["end_idx"], p["high_idx"], p["low_idx"]))
    pivots: list[dict] = []
    for pair in valid:
        low_pivot = {"idx": pair["low_idx"], "ts": pair["low_ts"], "value": pair["low_value"]}
        high_pivot = {"idx": pair["high_idx"], "ts": pair["high_ts"], "value": pair["high_value"]}
        if not pivots:
            pivots.append(low_pivot)
            pivots.append(high_pivot)
            continue
        if pivots[-1]["idx"] == low_pivot["idx"]:
            pivots[-1] = low_pivot
        else:
            pivots.append(low_pivot)
        if pivots[-1]["idx"] == high_pivot["idx"]:
            pivots[-1] = high_pivot
        else:
            pivots.append(high_pivot)
    return pivots


def _compress_major_pivots(minor_pivots: list[dict]) -> list[dict]:
    if len(minor_pivots) <= 2:
        return list(minor_pivots)

    # Stage 1: collapse same-direction extensions to dominant extremes.
    directional: list[dict] = [minor_pivots[0], minor_pivots[1]]
    for pivot in minor_pivots[2:]:
        a = directional[-2]
        b = directional[-1]
        d1 = float(b["value"]) - float(a["value"])
        d2 = float(pivot["value"]) - float(b["value"])
        if d1 == 0.0:
            directional[-1] = pivot
            continue
        if d1 * d2 > 0:
            if (d1 > 0 and float(pivot["value"]) >= float(b["value"])) or (d1 < 0 and float(pivot["value"]) <= float(b["value"])):
                directional[-1] = pivot
            continue
        directional.append(pivot)

    if len(directional) <= 2:
        return directional

    # Stage 2: remove low-prominence reversals; keep structurally meaningful turns.
    leg_sizes = [abs(float(directional[i]["value"]) - float(directional[i - 1]["value"])) for i in range(1, len(directional))]
    base_leg = statistics.median(leg_sizes) if leg_sizes else 0.0
    threshold = base_leg * 1.2

    major: list[dict] = [directional[0]]
    for i in range(1, len(directional) - 1):
        prev_p = directional[i - 1]
        cur_p = directional[i]
        next_p = directional[i + 1]
        left = abs(float(cur_p["value"]) - float(prev_p["value"]))
        right = abs(float(next_p["value"]) - float(cur_p["value"]))
        prominence = min(left, right)
        if prominence >= threshold:
            major.append(cur_p)
    major.append(directional[-1])

    # Deduplicate by index while preserving order.
    out: list[dict] = []
    for p in major:
        if out and int(out[-1]["idx"]) == int(p["idx"]):
            out[-1] = p
        else:
            out.append(p)
    return out


def _pivots_to_pairs(pivots: list[dict]) -> list[dict]:
    pairs: list[dict] = []
    for i in range(1, len(pivots)):
        a = pivots[i - 1]
        b = pivots[i]
        if int(a["idx"]) == int(b["idx"]):
            continue
        low_p = a if float(a["value"]) <= float(b["value"]) else b
        high_p = b if low_p is a else a
        pairs.append(
            {
                "low_idx": int(low_p["idx"]),
                "high_idx": int(high_p["idx"]),
                "low_value": float(low_p["value"]),
                "high_value": float(high_p["value"]),
            }
        )
    return pairs


def build_ontology_liquidity_model(bars: list[dict]) -> dict:
    if len(bars) < 5:
        return {"bias": "bearish", "minor_pairs": [], "major_pairs": [], "active_pair": None}

    bias = _resolve_liquidity_bias(bars)
    series_bear = [{"high": float(b["high"]), "low": float(b["low"])} for b in bars]
    series_bull = [{"high": -float(b["low"]), "low": -float(b["high"])} for b in bars]

    def _canonicalize_pairs(pairs: list[dict]) -> list[dict]:
        by_end: dict[int, dict] = {}
        for pair in pairs:
            end_idx = int(pair["end_idx"])
            current = by_end.get(end_idx)
            if current is None or int(pair["low_idx"]) > int(current["low_idx"]):
                by_end[end_idx] = pair

        by_peak: dict[int, dict] = {}
        for pair in by_end.values():
            peak_idx = int(pair["high_idx"])
            current = by_peak.get(peak_idx)
            if current is None or int(pair["low_idx"]) > int(current["low_idx"]):
                by_peak[peak_idx] = pair

        canonical = sorted(by_peak.values(), key=lambda p: (int(p["end_idx"]), int(p["high_idx"]), int(p["low_idx"])))
        return [
            {
                "low_idx": int(pair["low_idx"]),
                "high_idx": int(pair["high_idx"]),
                "end_idx": int(pair["end_idx"]),
                "low_value": float(pair["low_value"]),
                "high_value": float(pair["high_value"]),
            }
            for pair in canonical
        ]

    def detect_pairs(series: list[dict]) -> tuple[list[dict], dict | None]:
        detected: list[dict] = []
        active_candidates: list[dict] = []

        for ref_idx in range(0, len(series) - 1):
            start_idx: int | None = None
            termination_ref_idx = ref_idx
            max_high = float("-inf")
            max_high_idx = -1
            outside_base_idx: int | None = None
            outside_resolved = False
            inside_equal_low_ref_idx: int | None = None

            for i in range(ref_idx + 1, len(series)):
                cur = series[i]

                if start_idx is None:
                    effective_ref_idx = inside_equal_low_ref_idx if inside_equal_low_ref_idx is not None else ref_idx
                    effective_ref = series[effective_ref_idx]
                    is_inside = cur["high"] <= effective_ref["high"] and cur["low"] >= effective_ref["low"]
                    if is_inside and cur["low"] == effective_ref["low"]:
                        inside_equal_low_ref_idx = i
                        continue

                    is_outside = cur["high"] > effective_ref["high"] and cur["low"] < effective_ref["low"]
                    if is_outside:
                        start_idx = i
                        termination_ref_idx = effective_ref_idx
                        outside_base_idx = i
                        outside_resolved = False
                        max_high = float(cur["high"])
                        max_high_idx = i
                        continue

                    if cur["high"] > effective_ref["high"] and cur["low"] >= effective_ref["low"]:
                        start_idx = i
                        termination_ref_idx = effective_ref_idx
                        max_high = float(cur["high"])
                        max_high_idx = i
                        continue
                    continue

                if outside_base_idx is not None and not outside_resolved:
                    if cur["high"] > series[outside_base_idx]["high"]:
                        termination_ref_idx = outside_base_idx
                    outside_resolved = True

                if cur["high"] > max_high:
                    max_high = float(cur["high"])
                    max_high_idx = i

                if cur["low"] < series[termination_ref_idx]["low"]:
                    detected.append(
                        {
                            "low_idx": int(termination_ref_idx),
                            "high_idx": int(max_high_idx),
                            "end_idx": int(i),
                            "low_value": float(series[termination_ref_idx]["low"]),
                            "high_value": float(series[max_high_idx]["high"]),
                        }
                    )
                    break
            else:
                if start_idx is not None and max_high_idx >= 0:
                    active_candidates.append(
                        {
                            "low_idx": int(termination_ref_idx),
                            "high_idx": int(max_high_idx),
                            "low_value": float(series[termination_ref_idx]["low"]),
                            "high_value": float(series[max_high_idx]["high"]),
                        }
                    )

        detected_sorted = _canonicalize_pairs(detected)
        active_local = max(active_candidates, key=lambda p: (int(p["high_idx"]), int(p["low_idx"]))) if active_candidates else None
        return detected_sorted, active_local

    bear_pairs, bear_active = detect_pairs(series_bear)
    bull_pairs, bull_active = detect_pairs(series_bull)

    bull_pairs_natural = [
        {
            "low_idx": int(p["low_idx"]),
            "high_idx": int(p["high_idx"]),
            "end_idx": int(p.get("end_idx", p["high_idx"])),
            "low_value": -float(p["low_value"]),
            "high_value": -float(p["high_value"]),
        }
        for p in bull_pairs
    ]
    minor_pairs = bull_pairs_natural if bias == "bullish" else [
        {
            "low_idx": int(p["low_idx"]),
            "high_idx": int(p["high_idx"]),
            "end_idx": int(p.get("end_idx", p["high_idx"])),
            "low_value": float(p["low_value"]),
            "high_value": float(p["high_value"]),
        }
        for p in bear_pairs
    ]

    active_pair = None
    if bias == "bullish" and bull_active is not None:
        active_pair = {
            "low_idx": int(bull_active["low_idx"]),
            "high_idx": int(bull_active["high_idx"]),
            "low_value": -float(bull_active["low_value"]),
            "high_value": -float(bull_active["high_value"]),
            "status": "active",
        }
    if bias == "bearish" and bear_active is not None:
        active_pair = {
            "low_idx": int(bear_active["low_idx"]),
            "high_idx": int(bear_active["high_idx"]),
            "low_value": float(bear_active["low_value"]),
            "high_value": float(bear_active["high_value"]),
            "status": "active",
        }

    minor_pivots = _pairs_to_pivot_chain(minor_pairs, bars)
    major_pivots = _compress_major_pivots(minor_pivots)
    major_pairs = _pivots_to_pairs(major_pivots)

    return {
        "bias": bias,
        "minor_pairs": minor_pairs,
        "major_pairs": major_pairs,
        "minor_pivots": minor_pivots,
        "major_pivots": major_pivots,
        "active_pair": active_pair,
    }


def build_liquidity_overlay_data(bars: list[dict], model: dict) -> dict:
    segments: list[dict] = []

    def _pivots_to_segments(pivots: list[dict], color: str, size: int) -> None:
        for i in range(1, len(pivots)):
            start = pivots[i - 1]
            end = pivots[i]
            if int(start["idx"]) == int(end["idx"]):
                continue
            segments.append(
                {
                    "start": {"timestamp": int(start["ts"]), "value": float(start["value"])},
                    "end": {"timestamp": int(end["ts"]), "value": float(end["value"])},
                    "color": color,
                    "size": size,
                    "style": "solid",
                }
            )

    minor_pivots = [p for p in model.get("minor_pivots", []) if isinstance(p, dict)]
    major_pivots = [p for p in model.get("major_pivots", []) if isinstance(p, dict)]
    _pivots_to_segments(minor_pivots, "#f7c744", 1)
    _pivots_to_segments(major_pivots, "#3d73ff", 2)

    active_pair = model.get("active_pair")
    if isinstance(active_pair, dict):
        low_idx = int(active_pair.get("low_idx", -1))
        high_idx = int(active_pair.get("high_idx", -1))
        if low_idx >= 0 and high_idx >= 0 and low_idx < len(bars) and high_idx < len(bars):
            low_bar = bars[low_idx]
            high_bar = bars[high_idx]
            low_value = float(active_pair.get("low_value", 0.0))
            high_value = float(active_pair.get("high_value", 0.0))
            segments.append(
                {
                    "start": {"timestamp": int(low_bar["timestamp"]), "value": low_value},
                    "end": {"timestamp": int(high_bar["timestamp"]), "value": high_value},
                    "color": "#ff9b3d",
                    "size": 1,
                    "style": "dash",
                }
            )

    return {"segments": segments, "markers": []}
