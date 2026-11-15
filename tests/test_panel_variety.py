"""Tests for skills/buyer-panel/scripts/panel.py variety. Run: python -m unittest discover -s tests"""
import os
import shutil
import tempfile
import unittest

from test_panel import FIXTURES, NORMAL, jsonl, lines, run, run_json, write

UNIFORM = os.path.join(FIXTURES, "uniform-buyers")


def by_name(result):
    return {c["name"]: c for c in result["checks"]}


class NormalBuyers(unittest.TestCase):
    """The normal fixture: 7 buyers for a plan of 7, solo, studio and agency 2 each, school 1."""

    @classmethod
    def setUpClass(cls):
        cls.result, cls.code = run_json("variety", NORMAL)
        cls.checks = by_name(cls.result)

    def test_varied_buyers_pass_every_check(self):
        self.assertEqual(self.code, 0, self.result)
        self.assertEqual(self.result["failed"], [])
        self.assertIsNone(self.result["verdict_line"])

    def test_segment_shares_are_compared_with_the_plan(self):
        # school 1 of 7 against 0.1 is the widest gap, 0.043; one buyer in 7 is the tolerance
        self.assertEqual(self.checks["shares"]["value"], 0.043)
        self.assertTrue(self.checks["shares"]["passed"])

    def test_budget_spread_needs_three_buyers_in_a_segment(self):
        self.assertIsNone(self.checks["budget_spread"]["value"])
        self.assertTrue(self.checks["budget_spread"]["passed"])


class UniformBuyers(unittest.TestCase):
    """7 buyers for a plan of 8: six studio buyers at budget 30, two named Ana Ruiz, five saying too expensive."""

    @classmethod
    def setUpClass(cls):
        cls.result, cls.code = run_json("variety", UNIFORM)
        cls.checks = by_name(cls.result)

    def test_fails_every_variety_check_and_exits_1(self):
        self.assertEqual(self.code, 1, self.result)
        self.assertEqual(self.result["failed"], ["count", "shares", "budget_spread", "names", "objections"])

    def test_count_is_held_against_the_plans_size(self):
        self.assertEqual((self.checks["count"]["value"], self.checks["count"]["threshold"]), (7, "= 8"))

    def test_shares_gap_is_the_widest_segment_gap(self):
        # studio 6 of 7 against 0.5, solo 1 of 7 against 0.5: 0.357 each, over the tolerance of one buyer in 8
        self.assertEqual(self.checks["shares"]["value"], 0.357)
        self.assertEqual(self.checks["shares"]["threshold"], "<= 0.125")

    def test_budget_spread_is_the_narrowest_segment_span(self):
        # six studio budgets of 30 cover none of the plan's 10 to 50; solo has one buyer and is not measured
        self.assertEqual(self.checks["budget_spread"]["value"], 0)

    def test_duplicate_names_and_objections_name_their_buyers(self):
        self.assertEqual(self.checks["names"]["buyers"], ["b01", "b02"])
        # case and spacing aside, "Too expensive." five times
        self.assertEqual(self.checks["objections"]["buyers"], ["b01", "b02", "b03", "b04", "b05"])
        self.assertEqual((self.checks["names"]["value"], self.checks["objections"]["value"]), (2, 5))

    def test_text_output_is_a_table_and_a_rewrite_line(self):
        out = run("variety", UNIFORM)
        self.assertEqual(out.returncode, 1)
        rows = [x for x in out.stdout.splitlines() if x.startswith("| ")]
        self.assertEqual(len(rows), 1 + 5)
        self.assertIn("| count | buyers against the plan's size | 7 | = 8 | FAIL |", rows)
        self.assertIn("Rewrite the buyers before any interview: buyer count, segment shares, budget spread, "
                      "duplicate names, duplicate objections failed.", out.stdout)


class InvalidBuyers(unittest.TestCase):
    def test_buyers_outside_the_plan_are_invalid_records(self):
        with tempfile.TemporaryDirectory() as d:
            panel = os.path.join(d, "panel")
            shutil.copytree(NORMAL, panel)
            buyers = lines(os.path.join(panel, "buyers.jsonl"))
            buyers[0]["segment"] = "enterprise"
            write(panel, "buyers.jsonl", jsonl(buyers))
            result, code = run_json("variety", panel)
        self.assertEqual(code, 3)
        self.assertEqual([(e["line"], e["field"]) for e in result["errors"]], [(1, "segment")])

    def test_a_panel_without_a_plan_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            shutil.copy(os.path.join(NORMAL, "buyers.jsonl"), d)
            result, code = run_json("variety", d)
        self.assertEqual(code, 3)
        self.assertTrue(result["errors"][0]["file"].endswith("plan.json"))


if __name__ == "__main__":
    unittest.main()
