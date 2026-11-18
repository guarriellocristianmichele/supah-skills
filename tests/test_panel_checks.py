"""Tests for skills/buyer-panel/scripts/panel.py checks. Run: python -m unittest discover -s tests"""
import json
import os
import shutil
import tempfile
import unittest

from test_panel import FIXTURES, NORMAL, copy_round, jsonl, lines, run, run_json, write

NORMAL_R1 = os.path.join(NORMAL, "rounds", "r1")
CHECKS = os.path.join(FIXTURES, "checks")


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

    def test_similarity_is_the_top_reason_tags_share(self):
        # saves-time, already-paid and no-need 2 of 7 each; on a tie the first tag in name order is named
        self.assertEqual((self.checks["similarity"]["value"], self.checks["similarity"]["reason"]),
                         (0.286, "already-paid"))


def fixture_round(label):
    return os.path.join(CHECKS, "rounds", label)


class UniformRound(unittest.TestCase):
    """Every buyer judged 3 and tagged price-drop, in reactions that share little beyond "if the price drops"."""

    @classmethod
    def setUpClass(cls):
        cls.result, cls.code = run_json("checks", fixture_round("uniform"))
        cls.checks = by_name(cls.result)

    def test_fails_the_spread_and_similarity_checks_and_exits_1(self):
        self.assertEqual(self.code, 1, self.result)
        self.assertEqual(self.result["failed"], ["spread", "similarity"])

    def test_spread_is_zero(self):
        self.assertEqual(self.checks["spread"]["value"], 0)

    def test_similarity_is_the_share_of_buyers_giving_the_top_reason(self):
        # price-drop for all 7
        self.assertEqual(self.checks["similarity"]["value"], 1)
        self.assertEqual(self.checks["similarity"]["reason"], "price-drop")

    def test_reactions_in_their_own_words_pass_the_overlap_check(self):
        self.assertTrue(self.checks["overlap"]["passed"])


class EchoRound(unittest.TestCase):
    """One reaction repeated by every buyer, judged as the normal round was: intents and tags vary."""

    @classmethod
    def setUpClass(cls):
        cls.result, cls.code = run_json("checks", fixture_round("echo"))
        cls.checks = by_name(cls.result)

    def test_fails_only_the_overlap_check(self):
        self.assertEqual(self.code, 1, self.result)
        self.assertEqual(self.result["failed"], ["overlap"])

    def test_overlap_is_the_mean_word_overlap_between_reactions(self):
        # every pair of reactions is the same sentence: overlap 1
        self.assertEqual(self.checks["overlap"]["value"], 1)

    def test_varied_reasons_pass_the_similarity_check(self):
        # saves-time, already-paid and no-need 2 each, better-quotes 1: the top tag holds 2 of 7
        self.assertEqual(self.checks["similarity"]["value"], 0.286)


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


KEEP = os.path.join(FIXTURES, "keep", "rounds")


class KeepRate(unittest.TestCase):
    """Five buyers: four pay for Toggl or Harvest (b04 names Harvest beside a spreadsheet), b05 pays nothing."""

    def test_paying_buyers_who_all_walk_away_fail_only_the_keep_check(self):
        result, code = run_json("checks", os.path.join(KEEP, "walkaway"))
        keep = by_name(result)["keep"]
        self.assertEqual((code, result["failed"]), (1, ["keep"]), result)
        self.assertEqual((keep["value"], keep["buyers"]), (0, ["b01", "b02", "b03", "b04"]))
        self.assertEqual(result["verdict_line"], "Do not trust this round: keep rate failed.")
        self.assertIn("Paying buyers who chose nothing: b01, b02, b03, b04", run("checks", os.path.join(KEEP, "walkaway")).stdout)

    def test_keeping_a_tool_or_switching_to_the_offer_counts_as_staying(self):
        # b01 keeps Toggl, b02 keeps Harvest, b03 takes the offer, b04 chooses nothing: 3 of 4
        result, code = run_json("checks", os.path.join(KEEP, "kept"))
        keep = by_name(result)["keep"]
        self.assertEqual((code, keep["value"], keep["buyers"], keep["passed"]), (0, 0.75, ["b04"], True))

    def test_fewer_than_three_paying_users_is_not_measured_and_passes(self):
        # the normal round: only b03 (Toggl) and b06 (Harvest) pay for an option shown
        keep = by_name(run_json("checks", NORMAL_R1)[0])["keep"]
        self.assertEqual((keep["value"], keep["passed"]), (None, True))

    def test_the_label_counts_the_buyers_measured_not_the_minimum(self):
        walkaway = by_name(run_json("checks", os.path.join(KEEP, "walkaway"))[0])["keep"]
        normal = by_name(run_json("checks", NORMAL_R1)[0])["keep"]
        self.assertEqual((walkaway["measured"], normal["measured"]), (4, 2))
        self.assertIn("over 4 such buyers (measured from 3)", walkaway["what"])
        self.assertIn("over 2 such buyers (measured from 3)", normal["what"])
        self.assertIn("over 4 such buyers (measured from 3)", run("checks", os.path.join(KEEP, "walkaway")).stdout)


class PersonaCopy(unittest.TestCase):
    """The normal panel's seven buyers, with reactions that paste each buyer's own written objection."""

    def copied_round(self, d, own=True):
        r1 = copy_round(d)
        buyers = {b["id"]: b for b in lines(os.path.join(r1, "..", "..", "buyers.jsonl"))}
        ids = sorted(buyers)
        answers = lines(os.path.join(r1, "answers.jsonl"))
        for a in answers:
            source = a["buyer_id"] if own else ids[(ids.index(a["buyer_id"]) + 1) % len(ids)]
            a["reaction"] = buyers[source]["objection"] + " " + a["reaction"]
        write(r1, "answers.jsonl", jsonl(answers))
        return r1

    def test_pasting_the_own_objection_is_flagged_but_sets_no_verdict(self):
        with tempfile.TemporaryDirectory() as d:
            result, code = run_json("checks", self.copied_round(d))
            persona = by_name(result)["persona"]
            self.assertEqual((persona["value"], persona["passed"], persona["advisory"]), (1, False, True))
            self.assertLess(persona["p"], 0.05)
            self.assertNotIn("persona", result["failed"])
            self.assertEqual(code, 0, result)
            out = run("checks", self.copied_round(os.path.join(d, "again"))).stdout
            self.assertIn("| warn |", out)
            self.assertIn("Advisory, not part of the verdict: persona copying", out)

    def test_copying_another_buyers_objection_is_not_persona_copying(self):
        with tempfile.TemporaryDirectory() as d:
            persona = by_name(run_json("checks", self.copied_round(d, own=False))[0])["persona"]
            self.assertTrue(persona["passed"], persona)

    def test_reactions_in_their_own_words_pass(self):
        persona = by_name(run_json("checks", NORMAL_R1)[0])["persona"]
        self.assertEqual((persona["value"], persona["passed"]), (0, True))

    def test_the_label_counts_the_buyers_measured_not_the_minimum(self):
        # all seven buyers of the normal round wrote an objection of four words or more
        persona = by_name(run_json("checks", NORMAL_R1)[0])["persona"]
        self.assertEqual(persona["measured"], 7)
        self.assertIn("over 7 buyers (measured from 4)", persona["what"])


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
        self.assertEqual(len(rows), 1 + 8)                       # header and one row per check
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

    def test_advisory_checks_on_a_subset_say_so_and_do_not_stop(self):
        out = run("checks", fixture_round("uniform"), "--advisory")
        result, code = run_json("checks", fixture_round("uniform"), "--advisory")
        self.assertEqual((out.returncode, code), (0, 0))
        self.assertTrue(result["advisory"])
        self.assertEqual(result["failed"], ["spread", "similarity"])
        self.assertEqual(result["verdict_line"], "Advisory, on 7 buyers of a screening or try-out round: intent spread, "
                                                 "reason similarity failed. Read this round with care; it sets no "
                                                 "verdict of its own.")
        self.assertNotIn("Do not trust", out.stdout)
        self.assertIn("Advisory, on 7 buyers", out.stdout)

    def test_a_full_round_is_not_advisory(self):
        result, _ = run_json("checks", NORMAL_R1)
        self.assertFalse(result["advisory"])

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
