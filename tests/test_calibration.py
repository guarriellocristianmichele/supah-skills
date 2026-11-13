"""Tests for scripts/calibrate.py statistics and the shipped calibration.json."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "skills", "ai-slop-prose", "scripts"))
import calibrate  # noqa: E402

SCAN = os.path.join(ROOT, "skills", "ai-slop-prose", "scripts", "scan.py")
CALIBRATION = os.path.join(ROOT, "skills", "ai-slop-prose", "scripts", "calibration.json")
FIX = os.path.join(ROOT, "tests", "fixtures")


class Statistics(unittest.TestCase):
    def test_wilson_bounds(self):
        lo, up = calibrate.wilson(0, 1000)
        self.assertEqual(lo, 0.0)
        self.assertAlmostEqual(up, 0.00383, places=4)  # rule of three is 0.003; Wilson is a little wider
        lo, up = calibrate.wilson(50, 100)
        self.assertLess(lo, 0.5)
        self.assertGreater(up, 0.5)

    def test_clopper_pearson_zero_failures(self):
        self.assertAlmostEqual(calibrate.clopper_pearson_upper(0, 592), 1 - 0.05 ** (1 / 592), places=6)

    def test_conformal_threshold_controls_false_positives(self):
        scores = list(range(1, 1001))  # human scores 1..1000
        tau = calibrate.conformal(scores, 0.01)
        self.assertEqual(tau, 991)  # ceil(1001 * 0.99) = 991st smallest
        self.assertLessEqual(sum(s > tau for s in scores) / len(scores), 0.01)
        self.assertIsNone(calibrate.conformal(scores[:50], 0.01))  # too few for alpha

    def test_admission_is_false_positive_first(self):
        tier, _, _ = calibrate.admit(0, 1400, 80, 850, representative=True)
        self.assertEqual(tier, "S")
        tier, _, _ = calibrate.admit(40, 1400, 200, 850, representative=True)  # 2.9% of human docs
        self.assertEqual(tier, "W")
        tier, _, _ = calibrate.admit(2, 1400, 0, 270, representative=False)  # LR ignored
        self.assertEqual(tier, "M")
        self.assertEqual(calibrate.worse("S", "M"), "M")


class ShippedCalibration(unittest.TestCase):
    def setUp(self):
        with open(CALIBRATION, encoding="utf-8") as f:
            self.cal = json.load(f)

    def test_shape(self):
        for key in ("rules", "metrics", "demoted_words", "marked_min", "evidence_min", "alpha"):
            self.assertIn(key, self.cal)
        self.assertLessEqual(self.cal["alpha"], 0.01)

    def test_calibration_only_lowers_tiers(self):
        order = "SMW"
        for key, r in self.cal["rules"].items():
            self.assertGreaterEqual(order.index(r["tier"]), order.index(r["designed"]), key)

    def test_rules_exist_in_scanner(self):
        import scan
        known = {r[0] for r in scan.RULES} | {r[0] for r in scan.FIXES} | {"marked-word", "fragment-run",
                                                                           "title-case", "quote-mix"}
        for key in self.cal["rules"]:
            self.assertIn(key.split("/")[0], known, key)

    def test_end_to_end_with_calibration(self):
        env = dict(os.environ, PYTHONIOENCODING="utf-8", SUPAH_PROSE_HOME=tempfile.mkdtemp())
        env.pop("SUPAH_PROSE_NO_CALIBRATION", None)

        def scan(name):
            out = subprocess.run([sys.executable, SCAN, "--json", os.path.join(FIX, name)], capture_output=True,
                                 text=True, encoding="utf-8", env=env)
            return json.loads(out.stdout)[0]
        human = scan("human-en.txt")
        self.assertFalse([h for h in human["hits"] if h["tier"] in "SM" and not h["kept"]])
        slop = scan("slop-en.md")
        self.assertIn("chat-residue", {h["rule"] for h in slop["hits"] if h["tier"] == "S"})


if __name__ == "__main__":
    unittest.main()
