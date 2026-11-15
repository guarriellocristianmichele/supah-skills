"""Tests for skills/buyer-panel/scripts/panel.py. Run: python -m unittest discover -s tests"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "buyer-panel", "scripts", "panel.py")
FIX = os.path.join(ROOT, "tests", "fixtures", "buyer-panel")
NORMAL = os.path.join(FIX, "normal")


def run(*args):
    return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True, encoding="utf-8",
                          timeout=60)


def run_json(*args):
    out = run("--json", *args)
    return json.loads(out.stdout), out.returncode


def write(d, name, text):
    path = os.path.join(d, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return path


def lines(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def jsonl(records):
    return "".join(json.dumps(r) + "\n" for r in records)


class Validate(unittest.TestCase):
    def test_well_formed_buyers_pass(self):
        result, code = run_json("validate", os.path.join(NORMAL, "buyers.jsonl"))
        self.assertEqual(code, 0)
        self.assertEqual(result[0]["kind"], "buyers")
        self.assertEqual(result[0]["records"], 7)
        self.assertEqual(result[0]["errors"], [])

    def test_buyer_missing_a_field_is_rejected(self):
        good = lines(os.path.join(NORMAL, "buyers.jsonl"))
        broken = dict(good[1])
        del broken["objection"]
        broken["last_spend"] = "a lot"
        with tempfile.TemporaryDirectory() as d:
            path = write(d, "buyers.jsonl", jsonl([good[0], broken, good[0]]))
            result, code = run_json("validate", path)
        self.assertEqual(code, 3)
        problems = {(e["line"], e["field"]) for e in result[0]["errors"]}
        self.assertEqual(problems, {(2, "objection"), (2, "last_spend"), (3, "id")})

    def test_well_formed_answers_and_scores_pass(self):
        r1 = os.path.join(NORMAL, "rounds", "r1")
        result, code = run_json("validate", os.path.join(r1, "answers.jsonl"), os.path.join(r1, "scores.jsonl"))
        self.assertEqual(code, 0, result)
        self.assertEqual([(r["kind"], r["records"]) for r in result], [("answers", 7), ("scores", 7)])

    def test_answer_without_what_it_needs_is_rejected(self):
        good = lines(os.path.join(NORMAL, "rounds", "r1", "answers.jsonl"))
        no_give_up = dict(good[0], give_up="")                          # a BUY must say what it costs
        no_nothing = dict(good[1], options=["offer", "Toggl", "Harvest"])  # "buy nothing" always offered
        stray = dict(good[2], choice="Notion")                           # choice not among the options shown
        half_price = dict(good[3], price={"too_cheap": 6, "cheap": 11, "expensive": 18})
        with tempfile.TemporaryDirectory() as d:
            path = write(d, "answers.jsonl", jsonl([no_give_up, no_nothing, stray, half_price]))
            result, code = run_json("validate", path)
        self.assertEqual(code, 3)
        problems = {(e["line"], e["field"]) for e in result[0]["errors"]}
        self.assertEqual(problems, {(1, "give_up"), (2, "options"), (3, "choice"), (4, "price.too_expensive")})

    def test_score_outside_the_scale_is_rejected(self):
        good = lines(os.path.join(NORMAL, "rounds", "r1", "scores.jsonl"))
        with tempfile.TemporaryDirectory() as d:
            path = write(d, "scores.jsonl", jsonl([dict(good[0], intent=6), dict(good[1], intent=3.5),
                                                   dict(good[2], reason="Already Paid!"), good[3]]))
            result, code = run_json("validate", path)
        self.assertEqual(code, 3)
        problems = {(e["line"], e["field"]) for e in result[0]["errors"]}
        self.assertEqual(problems, {(1, "intent"), (2, "intent"), (3, "reason")})

    def test_brief_plan_and_round_pass(self):
        files = [os.path.join(NORMAL, "brief.json"), os.path.join(NORMAL, "plan.json"),
                 os.path.join(NORMAL, "rounds", "r1", "round.json")]
        result, code = run_json("validate", *files)
        self.assertEqual(code, 0, result)
        self.assertEqual([r["kind"] for r in result], ["brief", "plan", "round"])

    def test_plan_shares_must_add_up_and_ranges_be_ordered(self):
        plan = {"size": 100, "currency": "EUR", "segments": [
            {"name": "solo", "share": 0.5, "budget": [5, 20]},
            {"name": "studio", "share": 0.3, "budget": [40, 10]}]}
        with tempfile.TemporaryDirectory() as d:
            result, code = run_json("validate", write(d, "plan.json", json.dumps(plan)))
        self.assertEqual(code, 3)
        self.assertEqual({e["field"] for e in result[0]["errors"]}, {"segments.share", "segments[1].budget"})

    def test_round_needs_interview_mode_and_both_reserved_options(self):
        bad = {"label": "r1", "offer": "x", "price": 9, "currency": "EUR", "options": ["offer", "Toggl"],
               "model": "m", "interviews": "by hand", "batch_size": 0}
        with tempfile.TemporaryDirectory() as d:
            result, code = run_json("validate", write(d, "round.json", json.dumps(bad)))
        self.assertEqual(code, 3)
        self.assertEqual({e["field"] for e in result[0]["errors"]}, {"options", "interviews", "batch_size"})

    def test_buyers_are_checked_against_the_plan_beside_them(self):
        good = lines(os.path.join(NORMAL, "buyers.jsonl"))
        stray = dict(good[0], id="b08", segment="enterprise")
        rich = dict(good[1], id="b09", budget=90)     # solo budgets run 5 to 20
        with tempfile.TemporaryDirectory() as d:
            shutil.copy(os.path.join(NORMAL, "plan.json"), d)
            path = write(d, "buyers.jsonl", jsonl(good + [stray, rich]))
            result, code = run_json("validate", path)
        self.assertEqual(code, 3)
        problems = {(e["line"], e["field"]) for e in result[0]["errors"]}
        self.assertEqual(problems, {(8, "segment"), (9, "budget")})


class Aggregate(unittest.TestCase):
    """Expected values are worked by hand from the normal fixture (7 buyers, round r1)."""

    @classmethod
    def setUpClass(cls):
        cls.result, cls.code = run_json("aggregate", os.path.join(NORMAL, "rounds", "r1"))

    def test_buy_share_raw_and_discounted_with_the_scheme_named(self):
        self.assertEqual(self.code, 0, self.result)
        share = self.result["buy_share"]
        # b01, b02, b04 chose the offer: 3 of 7
        self.assertEqual(share["buyers"], 7)
        self.assertEqual(share["buy"], 3)
        self.assertAlmostEqual(share["raw"], 0.4286, places=4)
        # their intents 5, 4, 3 weigh 0.75 + 0.25 + 0.10 = 1.10; 1.10 / 7
        self.assertAlmostEqual(share["discounted"], 0.1571, places=4)
        self.assertEqual(share["weights"]["scheme"], "top-box 75/25/10/5/2 (Jamieson and Bass 1989)")
        self.assertEqual(share["weights"]["by_intent"], {"5": 0.75, "4": 0.25, "3": 0.1, "2": 0.05, "1": 0.02})

    def test_other_weights_are_named_as_custom(self):
        result, code = run_json("aggregate", os.path.join(NORMAL, "rounds", "r1"), "--weights", "1,0.5,0,0,0")
        self.assertEqual(code, 0)
        # intents 5, 4, 3 of the BUYs weigh 1 + 0.5 + 0 = 1.5; 1.5 / 7
        self.assertAlmostEqual(result["buy_share"]["discounted"], 0.2143, places=4)
        self.assertEqual(result["buy_share"]["weights"]["scheme"], "custom 100/50/0/0/0")

    def test_reasons_counted_with_ties_in_name_order(self):
        # passes: b03 and b06 already-paid, b05 and b07 no-need; buys: b01, b02 saves-time, b04 better-quotes
        self.assertEqual(self.result["pass_reasons"], [{"reason": "already-paid", "count": 2},
                                                       {"reason": "no-need", "count": 2}])
        self.assertEqual(self.result["buy_reasons"], [{"reason": "saves-time", "count": 2},
                                                      {"reason": "better-quotes", "count": 1}])

    def test_three_buyer_types_most_likely_to_buy(self):
        # solo 2 of 2 (0.75 + 0.25) / 2 = 0.5; studio 1 of 2, 0.10 / 2 = 0.05; agency and school 0,
        # agency first as the larger type
        types = self.result["buyer_types"]
        self.assertEqual([t["segment"] for t in types], ["solo", "studio", "agency"])
        self.assertEqual(types[0], {"segment": "solo", "buyers": 2, "buy": 2, "raw": 1.0, "discounted": 0.5})
        self.assertEqual(types[1], {"segment": "studio", "buyers": 2, "buy": 1, "raw": 0.5, "discounted": 0.05})

    def test_price_range_drops_out_of_order_answers(self):
        price = self.result["price"]
        # b05 (too cheap 12 above cheap 10) and b07 (all reversed) are dropped; 5 answers remain
        self.assertEqual(price["valid"], 5)
        self.assertEqual(price["dropped"], ["b05", "b07"])
        # too cheap (share answering >= p) reaches 0 at 9, where not cheap (1 - share cheap >= p) is still 0
        self.assertEqual(price["marginal_cheapness"], 9)
        # too expensive (share <= p) -0.2 against not expensive at 22, +0.2 at 25: halfway, 23.5
        self.assertEqual(price["marginal_expensiveness"], 23.5)
        self.assertEqual(price["range"], [9, 23.5])
        # too cheap 0.2 to 0 between 8 and 9 while too expensive stays 0: they meet at 9
        self.assertEqual(price["optimal"], 9)
        # cheap 0.2 against expensive 0 at 12, 0 against 0.2 at 15: halfway, 13.5
        self.assertEqual(price["indifference"], 13.5)
        self.assertTrue(price["upper_bound"])

    def test_round_states_model_and_independence(self):
        self.assertEqual(self.result["round"]["model"], "test-model-1")
        self.assertEqual((self.result["round"]["interviews"], self.result["round"]["batch_size"]), ("orchestrate", 4))
        self.assertEqual(self.result["missing"], {"answers": [], "scores": []})

    def test_buyer_table_has_every_buyer_in_panel_order(self):
        rows = self.result["rows"]
        self.assertEqual([r["buyer_id"] for r in rows], ["b01", "b02", "b03", "b04", "b05", "b06", "b07"])
        self.assertEqual(rows[2]["decision"], "PASS")
        self.assertEqual(rows[2]["choice"], "Toggl")
        self.assertEqual(rows[0]["give_up"], "one takeaway lunch a month")

    def test_text_output_is_the_reports_markdown_table(self):
        out = run("aggregate", os.path.join(NORMAL, "rounds", "r1"))
        self.assertEqual(out.returncode, 0)
        table = [x for x in out.stdout.splitlines() if x.startswith("| b0")]
        self.assertEqual(len(table), 7)
        self.assertIn("| b03 Lea Moretti | studio | 30 EUR | PASS (Toggl) | 2 | already-paid |", table[2])
        self.assertIn("| 4 / 9 / 15 / 25 |", table[2])
        self.assertIn("BUY 3 of 7: raw 42.9%, discounted 15.7%", out.stdout)
        self.assertIn("dropped 2 out-of-order answers (b05, b07)", out.stdout)


class Deal(unittest.TestCase):
    OPTIONS = "offer,Toggl,Harvest,nothing"

    def deal(self, d, *extra):
        out = os.path.join(d, "cards.jsonl")
        result, code = run_json("deal", "--buyers", os.path.join(NORMAL, "buyers.jsonl"), "--options", self.OPTIONS,
                                "--out", out, *extra)
        return result, code, lines(out) if os.path.exists(out) else []

    def test_batches_mix_segments_in_turn(self):
        with tempfile.TemporaryDirectory() as d:
            result, code, cards = self.deal(d, "--batch-size", "3", "--seed", "11")
        self.assertEqual(code, 0, result)
        # segments in order of first appearance (solo, studio, agency, school), one buyer from each in turn
        batches = {}
        for c in cards:
            batches.setdefault(c["batch"], []).append(c["buyer_id"])
        self.assertEqual(batches, {1: ["b01", "b03", "b05"], 2: ["b07", "b02", "b04"], 3: ["b06"]})
        self.assertEqual((result["seed"], result["batches"], result["batch_size"]), (11, 3, 3))

    def test_every_buyer_sees_every_option_in_a_recorded_order(self):
        with tempfile.TemporaryDirectory() as d:
            _, _, first = self.deal(d, "--seed", "11")
            _, _, again = self.deal(d, "--seed", "11")
        self.assertEqual(len(first), 7)
        for card in first:
            self.assertEqual(sorted(card["options"]), sorted(self.OPTIONS.split(",")))
        self.assertGreater(len({tuple(c["options"]) for c in first}), 1)
        self.assertEqual(first, again)

    def test_buy_nothing_is_never_left_out(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "cards.jsonl")
            proc = run("deal", "--buyers", os.path.join(NORMAL, "buyers.jsonl"), "--options", "offer,Toggl",
                       "--out", out)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("nothing", proc.stderr)


def copy_round(d):
    """A writable copy of the normal panel; returns the r1 round folder."""
    panel = os.path.join(d, "panel")
    shutil.copytree(NORMAL, panel)
    return os.path.join(panel, "rounds", "r1")


class RoundIntegrity(unittest.TestCase):
    def test_answer_from_an_unknown_buyer_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            r1 = copy_round(d)
            answers = lines(os.path.join(r1, "answers.jsonl"))
            answers[6]["buyer_id"] = "b99"
            write(r1, "answers.jsonl", jsonl(answers))
            result, code = run_json("aggregate", r1)
        self.assertEqual(code, 3)
        self.assertIn("unknown buyer b99", [e["problem"] for e in result["errors"]])

    def test_quote_must_come_from_the_reaction(self):
        with tempfile.TemporaryDirectory() as d:
            r1 = copy_round(d)
            scores = lines(os.path.join(r1, "scores.jsonl"))
            scores[0]["quote"] = "best tool I have ever seen"
            write(r1, "scores.jsonl", jsonl(scores))
            result, code = run_json("aggregate", r1)
        self.assertEqual(code, 3)
        self.assertEqual([e["field"] for e in result["errors"]], ["quote"])

    def test_options_must_be_the_rounds_options(self):
        with tempfile.TemporaryDirectory() as d:
            r1 = copy_round(d)
            answers = lines(os.path.join(r1, "answers.jsonl"))
            answers[0]["options"] = ["offer", "Toggl", "nothing"]   # Harvest was never shown
            write(r1, "answers.jsonl", jsonl(answers))
            result, code = run_json("aggregate", r1)
        self.assertEqual(code, 3)
        self.assertEqual([(e["line"], e["field"]) for e in result["errors"]], [(1, "options")])

    def test_unscored_and_unanswered_buyers_are_listed_and_left_out(self):
        with tempfile.TemporaryDirectory() as d:
            r1 = copy_round(d)
            answers = lines(os.path.join(r1, "answers.jsonl"))
            scores = lines(os.path.join(r1, "scores.jsonl"))
            write(r1, "answers.jsonl", jsonl(answers[1:]))            # b01 never interviewed
            write(r1, "scores.jsonl", jsonl(scores[:6]))              # b07 never judged
            result, code = run_json("aggregate", r1)
        self.assertEqual(code, 0, result)
        self.assertEqual(result["missing"], {"answers": ["b01"], "scores": ["b07"]})
        # b02 and b04 of the 5 left: 2/5 raw, (0.25 + 0.10) / 5 = 0.07
        self.assertEqual((result["buy_share"]["buy"], result["buy_share"]["buyers"]), (2, 5))
        self.assertAlmostEqual(result["buy_share"]["discounted"], 0.07, places=4)

    def test_batch_answer_files_count_as_one_round(self):
        with tempfile.TemporaryDirectory() as d:
            r1 = copy_round(d)
            answers = lines(os.path.join(r1, "answers.jsonl"))
            os.remove(os.path.join(r1, "answers.jsonl"))
            write(r1, os.path.join("answers", "batch-1.jsonl"), jsonl(answers[:4]))
            write(r1, os.path.join("answers", "batch-2.jsonl"), jsonl(answers[4:]))
            result, code = run_json("aggregate", r1)
        self.assertEqual(code, 0, result)
        self.assertEqual(result["buy_share"]["buyers"], 7)

    def test_same_buyer_in_two_batches_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            r1 = copy_round(d)
            answers = lines(os.path.join(r1, "answers.jsonl"))
            write(r1, os.path.join("answers", "batch-9.jsonl"), jsonl(answers[:1]))
            result, code = run_json("aggregate", r1)
        self.assertEqual(code, 3)
        self.assertIn("second record for b01", [e["problem"] for e in result["errors"]])


if __name__ == "__main__":
    unittest.main()
