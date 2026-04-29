import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
APP_PATH = ROOT / "services" / "inference-gateway" / "app.py"

spec = importlib.util.spec_from_file_location("signal_engine_app", APP_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def mk_feature_payload(ret_1: float, ewma: float, trend: float, pullback: float):
    return {
        "venue": "coinbase",
        "canonical_symbol": "BTCUSD",
        "timeframe": "1m",
        "event_ts": "2026-04-29T00:01:00Z",
        "bucket_start": "2026-04-29T00:01:00Z",
        "feature_set_version": "dev-00038.v1",
        "features": {
            "ret_1": ret_1,
            "ewma_return": ewma,
            "trend_score": trend,
            "phase_pullback": pullback,
            "range_body_ratio": 0.7,
        },
        "lineage": {
            "source_topic": "structure.snapshot.v1",
            "source_partition": 0,
            "source_offset": 42,
        },
    }


class SignalEngineTests(unittest.TestCase):
    def test_deterministic_scoring_same_input(self):
        payload = mk_feature_payload(0.02, 0.015, 1.0, 0.0)
        parsed = mod.parse_feature_payload(payload)
        s1, r1 = mod.deterministic_score(parsed.features)
        s2, r2 = mod.deterministic_score(parsed.features)
        self.assertEqual(s1, s2)
        self.assertEqual(r1, r2)

    def test_explainability_payload_has_reason_codes_and_refs(self):
        payload = mk_feature_payload(0.02, 0.015, 1.0, 0.0)
        parsed = mod.parse_feature_payload(payload)
        score, reasons = mod.deterministic_score(parsed.features)
        decision = mod.decide_signal(score, reasons)
        out = mod.build_signal_payload(parsed, decision)
        self.assertIn("reason_codes", out["signal"])
        self.assertGreater(len(out["signal"]["reason_codes"]), 0)
        self.assertIn("feature_refs", out["signal"])
        self.assertIn("lineage", out["signal"]["feature_refs"])

    def test_calibration_harness_outputs_distribution(self):
        samples = [
            mk_feature_payload(0.03, 0.02, 1.0, 0.0),
            mk_feature_payload(-0.03, -0.02, -1.0, 0.0),
            mk_feature_payload(0.0, 0.0, 0.0, 1.0),
        ]
        report = mod.run_calibration(samples)
        self.assertEqual(report["samples"], 3)
        self.assertEqual(report["status"], "ok")
        self.assertIn("buy", report)
        self.assertIn("sell", report)
        self.assertIn("hold", report)


if __name__ == "__main__":
    unittest.main()
