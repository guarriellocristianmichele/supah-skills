"""Tests for skills/buyer-panel/scripts/panel.py checks. Run: python -m unittest discover -s tests"""
import json
import os
import shutil
import tempfile
import unittest

from test_panel import FIX, NORMAL, copy_round, jsonl, lines, run, run_json, write

NORMAL_R1 = os.path.join(NORMAL, "rounds", "r1")
CHECKS = os.path.join(FIX, "checks")


def by_name(result):
    return {c["name"]: c for c in result["checks"]}


class NormalRound(unittest.TestCase):
    """Expected values worked by hand from the normal fixture (7 buyers, round r1)."""

    @classmethod
    def setUpClass(cls):
        cls.result, cls.code = run_json("checks", NORMAL_R1)
        cls.checks = by_name(cls.result)

    def test_a_normal_round_passes_every_check(self):
        self.assertEqual(self.code, 0, self.result)
        self.assertEqual([c["name"] for c in self.result["checks"] if not c["passed"]], [])

    def test_intent_spread_is_the_standard_deviation_of_intent(self):
        # intents 5, 4, 2, 3, 1, 2, 2: mean 19/7, squared deviations add up to 560/49, / 7, square root
        self.assertEqual(self.checks["spread"]["value"], 1.278)
        self.assertTrue(self.checks["spread"]["passed"])


def fixture_round(label):
    return os.path.join(CHECKS, "rounds", label)


class UniformRound(unittest.TestCase):
    """Every buyer judged 3; four buyers wrote reaction A, three wrote B, which differs by one word."""

    @classmethod
    def setUpClass(cls):
        cls.result, cls.code = run_json("checks", fixture_round("uniform"))
        cls.checks = by_name(cls.result)

    def test_fails_the_spread_and_similarity_checks_and_exits_1(self):
        self.assertEqual(self.code, 1, self.result)
        self.assertEqual(self.result["failed"], ["spread", "similarity"])

    def test_spread_is_zero(self):
        self.assertEqual(self.checks["spread"]["value"], 0)

    def test_similarity_is_the_mean_word_overlap_between_reactions(self):
        # without the stop words i, it, if, the, a: A = looks useful might try price drops little, B the same
        # with bit for little; A-A and B-B pairs (6 + 3) overlap 1, A-B pairs (12) overlap 6/8; (9 + 9) / 21
        self.assertEqual(self.checks["similarity"]["value"], 0.857)


class AgreeableRound(unittest.TestCase):
    """Six of seven buyers chose the offer, in reactions full of praise."""

    @classmethod
    def setUpClass(cls):
        cls.result, cls.code = run_json("checks", fixture_round("agreeable"))
        cls.checks = by_name(cls.result)

    def test_fails_the_praise_and_buy_share_checks_and_exits_1(self):
        self.assertEqual(self.code, 1, self.result)
        self.assertEqual(self.result["failed"], ["praise", "buy_share"])

    def test_praise_is_praise_words_per_100_words_of_reaction(self):
        # amazing love perfect, brilliant game-changer, fantastic love, great excellent, impressive, wonderful,
        # lovely: 12 praise words in 15 + 12 + 12 + 14 + 13 + 10 + 10 = 86 words; 12 / 86 * 100
        self.assertEqual(self.checks["praise"]["value"], 14.0)

    def test_buy_share_is_the_raw_share_choosing_the_offer(self):
        self.assertEqual(self.checks["buy_share"]["value"], 0.857)


class OrderBiasedRound(unittest.TestCase):
    """Five of seven buyers chose whatever was shown first; only one chose the offer."""

    @classmethod
    def setUpClass(cls):
        cls.result, cls.code = run_json("checks", fixture_round("order-biased"))
        cls.checks = by_name(cls.result)

    def test_fails_only_the_order_check_and_exits_1(self):
        self.assertEqual(self.code, 1, self.result)
        self.assertEqual(self.result["failed"], ["order"])

    def test_order_is_the_share_choosing_the_first_option_against_chance(self):
        # b01 Harvest, b02 nothing, b03 offer, b04 and b05 Toggl were first on their cards: 5 of 7;
        # four options on every card make chance 1 in 4
        self.assertEqual(self.checks["order"]["value"], 0.714)
        self.assertEqual(self.checks["order"]["chance"], 0.25)

    def test_a_normal_round_chose_the_first_option_never(self):
        result, _ = run_json("checks", NORMAL_R1)
        self.assertEqual(by_name(result)["order"]["value"], 0)


class Page(unittest.TestCase):
    def test_the_page_shows_the_checks_the_round_wrote(self):
        with tempfile.TemporaryDirectory() as d:
            panel = os.path.join(d, "panel")
            shutil.copytree(CHECKS, panel)
            uniform = os.path.join(panel, "rounds", "uniform")
            run_json("checks", uniform, "--out", os.path.join(uniform, "checks.json"))
            _, code = run_json("page", uniform)
            with open(os.path.join(uniform, "page.json"), encoding="utf-8") as f:
                data = json.load(f)
            with open(os.path.join(uniform, "page.html"), encoding="utf-8") as f:
                html = f.read()
        self.assertEqual(code, 0)
        self.assertEqual([c["name"] for c in data["checks"] if not c["passed"]], ["spread", "similarity"])
        self.assertIn('id="checks"', html)


class ReportOutput(unittest.TestCase):
    def test_a_failed_round_prints_the_checks_table_and_a_do_not_trust_verdict_line(self):
        out = run("checks", fixture_round("uniform"))
        self.assertEqual(out.returncode, 1)
        rows = [x for x in out.stdout.splitlines() if x.startswith("| ")]
        self.assertEqual(len(rows), 1 + 5)                       # header and one row per check
        self.assertIn("| spread | standard deviation of intent | 0 | >= 0.8 | FAIL |", rows)
        self.assertIn("Do not trust this round: intent spread, reason similarity failed.", out.stdout)

    def test_a_passed_round_has_no_verdict_line(self):
        out = run("checks", NORMAL_R1)
        self.assertEqual(out.returncode, 0)
        self.assertNotIn("Do not trust", out.stdout)
        result, _ = run_json("checks", NORMAL_R1)
        self.assertIsNone(result["verdict_line"])

    def test_buyer_types_are_marked_descriptive_with_the_reason(self):
        result, _ = run_json("checks", NORMAL_R1)
        self.assertTrue(result["segments"]["descriptive_only"])
        self.assertIn("flipped sign", result["segments"]["why"])
        self.assertIn("descriptive, not findings", run("checks", NORMAL_R1).stdout)

    def test_out_writes_the_json_result(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "checks.json")
            result, code = run_json("checks", fixture_round("agreeable"), "--out", path)
            with open(path, encoding="utf-8") as f:
                self.assertEqual(json.load(f), result)
        self.assertEqual(code, 1)

    def test_invalid_records_are_not_checked(self):
        with tempfile.TemporaryDirectory() as d:
            r1 = copy_round(d)
            answers = lines(os.path.join(r1, "answers.jsonl"))
            answers[6]["buyer_id"] = "b99"
            write(r1, "answers.jsonl", jsonl(answers))
            result, code = run_json("checks", r1)
        self.assertEqual(code, 3)
        self.assertNotIn("checks", result)


if __name__ == "__main__":
    unittest.main()
