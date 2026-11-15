"""Tests for skills/buyer-panel/scripts/panel.py, price mode. Run: python -m unittest discover -s tests"""
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_panel import FIXTURES, NORMAL, jsonl, lines, run, run_json, write  # noqa: E402

PRICE = os.path.join(FIXTURES, "price")
ROUNDS = [os.path.join(PRICE, "rounds", label) for label in ("p1-9", "p1-14", "p1-24")]


class Revenue(unittest.TestCase):
    """Expected values are worked by hand from the price fixture: the normal fixture's 7 buyers at 9, 14 and 24 EUR.

    BUYs and their intents (weights 75/25/10/5/2):
      9 EUR:  b01 5, b02 5, b04 3, b06 2  ->  0.75 + 0.75 + 0.10 + 0.05 = 1.65 discounted buyers
      14 EUR: b01 5, b02 4, b04 3         ->  0.75 + 0.25 + 0.10        = 1.10
      24 EUR: b01 4, b02 2, b04 2         ->  0.25 + 0.05 + 0.05        = 0.35
    """

    @classmethod
    def setUpClass(cls):
        cls.result, cls.code = run_json("revenue", *ROUNDS)

    def test_each_price_shows_raw_and_discounted_buyers_and_revenue(self):
        self.assertEqual(self.code, 0, self.result)
        rows = {r["price"]: r for r in self.result["rounds"]}
        self.assertEqual(sorted(rows), [9, 14, 24])
        self.assertEqual([(rows[p]["buy"], rows[p]["buyers"]) for p in (9, 14, 24)], [(4, 7), (3, 7), (3, 7)])
        self.assertAlmostEqual(rows[9]["discounted_buyers"], 1.65, places=4)
        self.assertAlmostEqual(rows[14]["discounted_buyers"], 1.10, places=4)
        self.assertAlmostEqual(rows[24]["discounted_buyers"], 0.35, places=4)
        # revenue = price x discounted buyers: 9 x 1.65, 14 x 1.10, 24 x 0.35
        self.assertAlmostEqual(rows[9]["revenue"], 14.85, places=2)
        self.assertAlmostEqual(rows[14]["revenue"], 15.40, places=2)
        self.assertAlmostEqual(rows[24]["revenue"], 8.40, places=2)
        # shares of the 7: 4/7, 1.65/7; 3/7, 1.10/7; 3/7, 0.35/7
        self.assertAlmostEqual(rows[9]["raw"], 0.5714, places=4)
        self.assertAlmostEqual(rows[9]["discounted"], 0.2357, places=4)
        self.assertAlmostEqual(rows[24]["discounted"], 0.05, places=4)

    def test_the_price_that_earns_most_is_named_on_discounted_buyers(self):
        # 15.40 at 14 beats 14.85 at 9 and 8.40 at 24
        self.assertEqual(self.result["best"], {"label": "p1-14", "price": 14, "currency": "EUR", "revenue": 15.4})
        # relative revenue: each price's revenue over the best one's
        rel = {r["price"]: r["relative"] for r in self.result["rounds"]}
        self.assertAlmostEqual(rel[9], 0.9643, places=4)     # 14.85 / 15.40
        self.assertEqual(rel[14], 1.0)
        self.assertAlmostEqual(rel[24], 0.5455, places=4)    # 8.40 / 15.40

    def test_raw_buyers_would_pick_another_price(self):
        # raw revenue 9 x 4 = 36, 14 x 3 = 42, 24 x 3 = 72: stated intent alone would pick 24
        raw = {r["price"]: r["raw_revenue"] for r in self.result["rounds"]}
        self.assertEqual(raw, {9: 36, 14: 42, 24: 72})
        self.assertEqual(self.result["best_raw"], {"label": "p1-24", "price": 24, "currency": "EUR", "revenue": 72})
        self.assertTrue(self.result["upper_bound"])

    def test_text_output_is_the_reports_price_table(self):
        out = run("revenue", *ROUNDS)
        self.assertEqual(out.returncode, 0)
        table = [x for x in out.stdout.splitlines() if x.startswith("| ") and "EUR" in x]
        self.assertEqual(len(table), 3)
        self.assertEqual(table[0], "| 9 EUR | p1-9 | 4 of 7 (57.1%) | 23.6% | 1.65 | 14.85 EUR | 96.4% |")
        self.assertEqual(table[1], "| 14 EUR | p1-14 | 3 of 7 (42.9%) | 15.7% | 1.1 | 15.4 EUR | 100.0% |")
        self.assertIn("Earns most: 14 EUR (p1-14)", out.stdout)
        self.assertIn("raw buyers alone would pick 24 EUR", out.stdout)
        self.assertIn("upper bound", out.stdout)

    def test_every_price_counts_the_same_buyers(self):
        self.assertEqual(self.result["left_out"], [])
        self.assertEqual(self.result["buyers"], 7)


def copy_panel(d):
    """A writable copy of the price panel; returns its three round folders."""
    panel = os.path.join(d, "panel")
    shutil.copytree(PRICE, panel)
    return [os.path.join(panel, "rounds", label) for label in ("p1-9", "p1-14", "p1-24")]


class SameBuyers(unittest.TestCase):
    def test_a_buyer_missing_from_one_round_is_left_out_of_all(self):
        with tempfile.TemporaryDirectory() as d:
            p9, p14, p24 = copy_panel(d)
            answers = lines(os.path.join(p9, "answers.jsonl"))
            write(p9, "answers.jsonl", jsonl([a for a in answers if a["buyer_id"] != "b06"]))
            result, code = run_json("revenue", p9, p14, p24)
        self.assertEqual(code, 0, result)
        self.assertEqual(result["left_out"], ["b06"])
        self.assertEqual(result["buyers"], 6)
        rows = {r["price"]: r for r in result["rounds"]}
        self.assertEqual([rows[p]["buyers"] for p in (9, 14, 24)], [6, 6, 6])
        # without b06 (intent 2 at 9 EUR): 0.75 + 0.75 + 0.10 = 1.60, 9 x 1.60 = 14.40
        self.assertAlmostEqual(rows[9]["discounted_buyers"], 1.60, places=4)
        self.assertAlmostEqual(rows[9]["revenue"], 14.40, places=2)
        # b06 never bought at 14 or 24: unchanged
        self.assertAlmostEqual(rows[14]["revenue"], 15.40, places=2)
        self.assertEqual(result["best"]["price"], 14)


class Prices(unittest.TestCase):
    def test_three_prices_come_from_the_first_rounds_range(self):
        # the normal r1 range runs 9 to 23.5 with the indifference point at 13.5 (worked in test_panel.py)
        result, code = run_json("prices", os.path.join(NORMAL, "rounds", "r1"))
        self.assertEqual(code, 0, result)
        self.assertEqual(result["prices"], [9, 13.5, 23.5])
        self.assertEqual((result["from"], result["currency"]), ("r1", "EUR"))
        self.assertTrue(result["upper_bound"])

    def test_no_range_means_no_prices_to_propose(self):
        with tempfile.TemporaryDirectory() as d:
            panel = os.path.join(d, "panel")
            shutil.copytree(NORMAL, panel)
            r1 = os.path.join(panel, "rounds", "r1")
            answers = lines(os.path.join(r1, "answers.jsonl"))
            for a in answers:     # the same price four times is out of order: all are dropped, no curve crosses
                a["price"] = {"too_cheap": 10, "cheap": 10, "expensive": 10, "too_expensive": 10}
            write(r1, "answers.jsonl", jsonl(answers))
            result, code = run_json("prices", r1)
        self.assertEqual(code, 0, result)
        self.assertIsNone(result["prices"])
        self.assertEqual(result["dropped"], 7)


class Refused(unittest.TestCase):
    """Price rounds compare one panel and one offer at different prices; anything else is bad usage (exit 2)."""

    def edit_round(self, d, index, **fields):
        rounds = copy_panel(d)
        path = os.path.join(rounds[index], "round.json")
        with open(path, encoding="utf-8") as f:
            meta = json.load(f)
        write(rounds[index], "round.json", json.dumps(dict(meta, **fields)))
        return rounds

    def test_two_rounds_at_the_same_price(self):
        with tempfile.TemporaryDirectory() as d:
            out = run("revenue", *self.edit_round(d, 2, price=14))
        self.assertEqual(out.returncode, 2)
        self.assertIn("price", out.stderr)

    def test_a_round_with_another_offer(self):
        with tempfile.TemporaryDirectory() as d:
            out = run("revenue", *self.edit_round(d, 1, offer="Tickr Pro: the same, with invoices."))
        self.assertEqual(out.returncode, 2)
        self.assertIn("offer", out.stderr)

    def test_a_round_in_another_currency(self):
        with tempfile.TemporaryDirectory() as d:
            out = run("revenue", *self.edit_round(d, 0, currency="USD"))
        self.assertEqual(out.returncode, 2)
        self.assertIn("currency", out.stderr)

    def test_a_round_of_another_panel(self):
        with tempfile.TemporaryDirectory() as d:
            p9, p14, _ = copy_panel(d)
            out = run("revenue", p9, p14, os.path.join(NORMAL, "rounds", "r1"))
        self.assertEqual(out.returncode, 2)
        self.assertIn("panel", out.stderr)

    def test_one_round_is_not_a_comparison(self):
        out = run("revenue", ROUNDS[0])
        self.assertEqual(out.returncode, 2)

    def test_invalid_records_in_any_round(self):
        with tempfile.TemporaryDirectory() as d:
            p9, p14, p24 = copy_panel(d)
            scores = lines(os.path.join(p24, "scores.jsonl"))
            scores[0]["intent"] = 7
            write(p24, "scores.jsonl", jsonl(scores))
            result, code = run_json("revenue", p9, p14, p24)
        self.assertEqual(code, 3)
        self.assertEqual([e["field"] for e in result["errors"]], ["intent"])


if __name__ == "__main__":
    unittest.main()
