"""Tests for skills/buyer-panel/scripts/panel.py, mode test. Run: python -m unittest discover -s tests"""
import json
import os
import tempfile
import unittest

from test_panel import FIXTURES, NORMAL, copy_round, run, run_json, write

KIT = os.path.join(FIXTURES, "test-kit", "test.json")


def kit(**changes):
    with open(KIT, encoding="utf-8") as f:
        record = json.load(f)
    record.update(changes)
    return record


def validate(record):
    with tempfile.TemporaryDirectory() as d:
        path = write(d, "test.json", json.dumps(record))
        result, code = run_json("validate", path)
    return {e["field"]: e["problem"] for e in result[0]["errors"]}, code


class Thresholds(unittest.TestCase):
    def test_well_formed_thresholds_pass(self):
        result, code = run_json("validate", KIT)
        self.assertEqual(code, 0)
        self.assertEqual(result[0]["kind"], "test")
        self.assertEqual(result[0]["errors"], [])

    def test_go_must_sit_above_stop_as_shares_of_one(self):
        errors, code = validate(kit(thresholds={"signups": {"go": 0.02, "stop": 0.02},
                                                "preorders": {"go": 1.5, "stop": 0},
                                                "commitments": {"go": 0.4}}))
        self.assertEqual(code, 3)
        self.assertEqual(set(errors), {"thresholds.signups", "thresholds.preorders.go",
                                       "thresholds.commitments.stop"})
        self.assertIn("below go", errors["thresholds.signups"])

    def test_only_the_three_real_test_metrics_count(self):
        errors, code = validate(kit(thresholds={"likes": {"go": 0.5, "stop": 0.1}}))
        self.assertEqual(code, 3)
        self.assertIn("thresholds.likes", errors)
        errors, _ = validate(kit(thresholds={}))
        self.assertIn("thresholds", errors)

    def test_sample_covers_what_each_share_is_taken_of(self):
        errors, code = validate(kit(sample={"interviews": 5}))
        self.assertEqual(code, 3)
        self.assertEqual(set(errors), {"sample.visits"})
        only_interviews = {"commitments": {"go": 0.4, "stop": 0.2}}
        errors, code = validate(kit(sample={"interviews": 5}, thresholds=only_interviews))
        self.assertEqual((errors, code), ({}, 0))
        errors, _ = validate(kit(sample={"visits": 300, "interviews": 0}))
        self.assertEqual(set(errors), {"sample.interviews"})

    def test_the_test_ends_on_a_real_date_after_it_was_written(self):
        errors, code = validate(kit(ends="2026-11-01"))
        self.assertEqual(code, 3)
        self.assertEqual(set(errors), {"ends"})
        errors, _ = validate(kit(written="15/11/2026"))
        self.assertEqual(set(errors), {"written"})

    def test_objections_are_reason_tags(self):
        errors, code = validate(kit(objections=["Already paid"]))
        self.assertEqual((set(errors), code), ({"objections"}, 3))
        errors, _ = validate(kit(objections=[]))
        self.assertEqual(set(errors), {"objections"})


R1 = os.path.join(NORMAL, "rounds", "r1")


class Objections(unittest.TestCase):
    def test_top_pass_reasons_with_each_buyers_words_and_spend(self):
        result, code = run_json("objections", R1)
        self.assertEqual(code, 0)
        # PASS in r1: b03 and b06 already-paid, b05 and b07 no-need; a tie goes in name order
        self.assertEqual([(o["reason"], o["count"]) for o in result["objections"]],
                         [("already-paid", 2), ("no-need", 2)])
        self.assertEqual(result["objections"][0]["buyers"], [
            {"buyer_id": "b03", "segment": "studio", "quote": "We already pay for Toggl and the team knows it.",
             "current_solution": "Toggl", "last_spend": 36},
            {"buyer_id": "b06", "segment": "agency", "quote": "Harvest is paid through next year",
             "current_solution": "Harvest", "last_spend": 120}])
        self.assertEqual([b["buyer_id"] for b in result["objections"][1]["buyers"]], ["b05", "b07"])

    def test_names_the_likely_buyer_type_and_what_the_panel_predicted(self):
        result, _ = run_json("objections", R1)
        self.assertEqual(result["likely_type"], "solo")
        # 3 of 7 chose the offer, at intents 5, 4 and 3: (0.75 + 0.25 + 0.1) / 7
        self.assertEqual(result["predicted"], {"buyers": 7, "buy": 3, "raw": 0.4286, "discounted": 0.1571})
        self.assertEqual((result["round"], result["price"], result["currency"]), ("r1", 9, "EUR"))

    def test_top_limits_the_objections(self):
        result, _ = run_json("objections", R1, "--top", "1")
        self.assertEqual([o["reason"] for o in result["objections"]], ["already-paid"])

    def test_text_output_traces_every_quote_to_a_buyer(self):
        out = run("objections", R1)
        self.assertEqual(out.returncode, 0)
        for bid in ("b03", "b05", "b06", "b07"):
            self.assertIn(bid, out.stdout)

    def test_invalid_round_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            round_dir = copy_round(d)
            with open(os.path.join(round_dir, "scores.jsonl"), "a", encoding="utf-8") as f:
                f.write('{"buyer_id": "b99", "round": "r1", "intent": 2, "reason": "x", "quote": "y"}\n')
            result, code = run_json("objections", round_dir)
        self.assertEqual(code, 3)
        self.assertTrue(result["errors"])


if __name__ == "__main__":
    unittest.main()
