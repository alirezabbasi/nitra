import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
APP_PATH = ROOT / "services" / "feature-service" / "app.py"

spec = importlib.util.spec_from_file_location("feature_service_app", APP_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def mk_payload(close: float, minute: int):
    ts = f"2026-04-29T00:{minute:02d}:00Z"
    return {
        "venue": "coinbase",
        "canonical_symbol": "BTCUSD",
        "timeframe": "1m",
        "bucket_start": ts,
        "last_event_ts": ts,
        "input_bar": {
            "open": close - 1.0,
            "high": close + 1.0,
            "low": close - 2.0,
            "close": close,
        },
        "state": {
            "trend": "bullish",
            "phase": "extension",
            "objective": "buy_side",
        },
        "transition_reason": "extension",
    }


class FeatureServiceTests(unittest.TestCase):
    def test_reproducible_features_same_input(self):
        parsed = mod.parse_structure_payload(mk_payload(101.0, 1))
        vec1 = mod.compute_feature_vector(parsed, None)
        vec2 = mod.compute_feature_vector(parsed, None)
        self.assertEqual(vec1, vec2)

    def test_pit_no_lookahead_guard_on_state_timestamp(self):
        first = mod.parse_structure_payload(mk_payload(101.0, 1))
        state = mod.next_feature_state(first, mod.compute_feature_vector(first, None))

        second = mod.parse_structure_payload(mk_payload(103.0, 2))
        vector = mod.compute_feature_vector(second, state)
        self.assertGreater(vector["ret_1"], 0.0)
        self.assertTrue(state.last_bucket_start.isoformat().startswith("2026-04-29T00:01:00"))

    def test_online_offline_consistency_check(self):
        parsed = mod.parse_structure_payload(mk_payload(105.0, 3))
        online = mod.compute_feature_vector(parsed, None)
        offline = dict(online)
        ok, reason = mod.compare_online_offline_features(online, offline)
        self.assertTrue(ok)
        self.assertEqual(reason, "ok")


if __name__ == "__main__":
    unittest.main()
