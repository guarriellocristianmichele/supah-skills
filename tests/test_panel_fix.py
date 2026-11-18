"""Tests for skills/buyer-panel/scripts/panel.py diff (the fix mode). Run: python -m unittest discover -s tests"""
import json
import os
import shutil
import tempfile
import unittest

from test_panel import FIXTURES, NORMAL, jsonl, lines, run, run_json, write

FIX_MODE = os.path.join(FIXTURES, "fix")


def two_rounds(d):
    """The normal panel with round r2 of the fix fixture beside r1; returns (r1, r2) round folders."""
    panel = os.path.join(d, "panel")
    shutil.copytree(NORMAL, panel)
    shutil.copytree(FIX_MODE, panel, dirs_exist_ok=True)
    return os.path.join(panel, "rounds", "r1"), os.path.join(panel, "rounds", "r2")


class Diff(unittest.TestCase):
    """r1 is the normal round; r2 shows the same seven buyers an offer that answers already-paid.
    Expected values are worked by hand from the two fixture rounds."""

    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as d:
            r1, r2 = two_rounds(d)
            cls.result, cls.code = run_json("diff", r1, r2)
            cls.text = run("diff", r1, r2)

    def test_flips_both_ways(self):
        self.assertEqual(self.code, 0, self.result)
        # b03 left Toggl for the offer; b02 left the offer for nothing
        self.assertEqual(self.result["flips"], {"pass_to_buy": ["b03"], "buy_to_pass": ["b02"]})

    def test_every_change_of_choice_is_a_switch_even_between_competitors(self):
        # b06 stayed a PASS but moved from Harvest to Toggl
        self.assertEqual(self.result["switches"], [{"buyer_id": "b02", "from": "offer", "to": "nothing"},
                                                   {"buyer_id": "b03", "from": "Toggl", "to": "offer"},
                                                   {"buyer_id": "b06", "from": "Harvest", "to": "Toggl"}])

    def test_choices_counted_per_option_in_both_rounds(self):
        # r1: offer b01 b02 b04, Toggl b03, Harvest b06, nothing b05 b07
        # r2: offer b01 b03 b04, Toggl b03's place taken by b06, Harvest nobody, nothing b02 b05 b07
        self.assertEqual(self.result["choices"], [{"option": "offer", "before": 3, "after": 3},
                                                  {"option": "Toggl", "before": 1, "after": 1},
                                                  {"option": "Harvest", "before": 1, "after": 0},
                                                  {"option": "nothing", "before": 2, "after": 3}])

    def test_buy_share_raw_and_discounted_before_and_after(self):
        share = self.result["buy_share"]
        # 3 of 7 in both rounds: no change raw
        self.assertEqual((share["before"]["buy"], share["after"]["buy"], share["before"]["buyers"]), (3, 3, 7))
        self.assertEqual(share["raw_change"], 0)
        # r1 intents of the BUYs 5, 4, 3: 0.75 + 0.25 + 0.10 = 1.10; r2 5, 5, 3: 0.75 + 0.75 + 0.10 = 1.60
        self.assertAlmostEqual(share["before"]["discounted"], 0.1571, places=4)
        self.assertAlmostEqual(share["after"]["discounted"], 0.2286, places=4)
        # (1.60 - 1.10) / 7
        self.assertAlmostEqual(share["discounted_change"], 0.0714, places=4)
        self.assertEqual(share["scheme"], "top-box 75/25/10/5/2 (Jamieson and Bass 1989)")

    def test_intent_shift_on_the_anchor_scale(self):
        intent = self.result["intent"]
        # r1 5 4 2 3 1 2 2 = 19; r2 5 2 5 3 1 2 2 = 20; over 7 buyers
        self.assertAlmostEqual(intent["before"], 2.7143, places=4)
        self.assertAlmostEqual(intent["after"], 2.8571, places=4)
        self.assertAlmostEqual(intent["change"], 0.1429, places=4)
        # b03 up from 2 to 5, b02 down from 4 to 2
        self.assertEqual((intent["up"], intent["down"], intent["same"]), (["b03"], ["b02"], 5))

    def test_new_top_reasons_and_the_ones_gone(self):
        passes = self.result["pass_reasons"]
        # r1 passes: b03 b06 already-paid, b05 b07 no-need; r2 passes: b02 b07 no-need, b06 retraining,
        # b05 vendor-approval
        self.assertEqual(passes["before"], [{"reason": "already-paid", "count": 2}, {"reason": "no-need", "count": 2}])
        self.assertEqual(passes["after"], [{"reason": "no-need", "count": 2}, {"reason": "retraining", "count": 1},
                                           {"reason": "vendor-approval", "count": 1}])
        self.assertEqual((passes["new"], passes["gone"]), (["retraining", "vendor-approval"], ["already-paid"]))
        buys = self.result["buy_reasons"]
        # r1 buys: b01 b02 saves-time, b04 better-quotes; r2 buys: b01 saves-time, b03 free-switch, b04 better-quotes
        self.assertEqual((buys["new"], buys["gone"]), (["free-switch"], []))

    def test_price_shift_on_the_card_and_in_the_range(self):
        price = self.result["price"]
        self.assertEqual((price["card"]["before"], price["card"]["after"], price["card"]["change"]), (9, 9, 0))
        # only b03 moved: too expensive 25 -> 30. At 25 too expensive (share <= 25) is now 0, as is not
        # expensive (1 - share expensive <= 25): they meet at 25 instead of 23.5. The low end stays at 9.
        self.assertEqual(price["before"]["range"], [9, 23.5])
        self.assertEqual(price["after"]["range"], [9, 25])
        self.assertEqual(price["range_change"], [0, 1.5])
        self.assertEqual((price["optimal_change"], price["indifference_change"]), (0, 0))
        # b05 and b07 answered out of order in both rounds
        self.assertEqual((price["before"]["dropped"], price["after"]["dropped"]), (["b05", "b07"], ["b05", "b07"]))

    def test_rounds_named_and_every_buyer_shown_with_what_changed(self):
        self.assertEqual((self.result["before"]["label"], self.result["after"]["label"]), ("r1", "r2"))
        self.assertEqual(self.result["buyers"], {"both": 7, "only_before": [], "only_after": []})
        rows = {r["buyer_id"]: r for r in self.result["rows"]}
        self.assertEqual([r["buyer_id"] for r in self.result["rows"]], ["b01", "b02", "b03", "b04", "b05", "b06", "b07"])
        self.assertEqual({b: r["change"] for b, r in rows.items()},
                         {"b01": "same", "b02": "buy-to-pass", "b03": "pass-to-buy", "b04": "same", "b05": "same",
                          "b06": "switch", "b07": "same"})
        b03 = rows["b03"]
        self.assertEqual((b03["name"], b03["segment"]), ("Lea Moretti", "studio"))
        self.assertEqual({k: b03["before"][k] for k in ("choice", "decision", "intent", "reason")},
                         {"choice": "Toggl", "decision": "PASS", "intent": 2, "reason": "already-paid"})
        self.assertEqual(b03["after"]["quote"], "we pay nothing until the plan ends, the switch costs us little")
        self.assertEqual(rows["b05"]["after"]["reason"], "vendor-approval")

    def test_text_output_is_the_reports_diff(self):
        out = self.text
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("r1 -> r2: 7 buyers in both rounds", out.stdout)
        self.assertIn("BUY 3 of 7 -> 3 of 7: raw 42.9% -> 42.9% (+0.0 points), "
                      "discounted 15.7% -> 22.9% (+7.1 points)", out.stdout)
        self.assertIn("PASS to BUY: b03. BUY to PASS: b02.", out.stdout)
        self.assertIn("Switches: b02 offer -> nothing, b03 Toggl -> offer, b06 Harvest -> Toggl", out.stdout)
        self.assertIn("Choices: offer 3 -> 3, Toggl 1 -> 1, Harvest 1 -> 0, nothing 2 -> 3", out.stdout)
        self.assertIn("Mean intent 2.71 -> 2.86 (+0.14): up b03; down b02; 5 the same", out.stdout)
        self.assertIn("Top reasons to pass: already-paid 2, no-need 2 -> no-need 2, retraining 1, vendor-approval 1 "
                      "(new: retraining, vendor-approval; gone: already-paid)", out.stdout)
        self.assertIn("Card price 9 -> 9 EUR; price range (upper bound) 9 to 23.5 -> 9 to 25 EUR", out.stdout)
        table = [x for x in out.stdout.splitlines() if x.startswith("| b0")]
        self.assertEqual(len(table), 7)
        self.assertEqual(table[2], '| b03 Lea Moretti | studio | PASS to BUY | PASS (Toggl) | BUY | 2 -> 5 | '
                                   'already-paid -> free-switch | "we pay nothing until the plan ends, the switch '
                                   'costs us little" |')
        self.assertIn("| b06 Raj Patel | agency | switch | PASS (Harvest) | PASS (Toggl) | 2 -> 2 |", table[5])

    def test_out_keeps_the_json_beside_the_round(self):
        with tempfile.TemporaryDirectory() as d:
            r1, r2 = two_rounds(d)
            path = os.path.join(r2, "diff.json")
            out = run("diff", r1, r2, "--out", path)
            with open(path, encoding="utf-8") as f:
                kept = json.load(f)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(kept["flips"], self.result["flips"])


class Screening(unittest.TestCase):
    def test_a_round_shown_to_some_buyers_compares_only_those(self):
        with tempfile.TemporaryDirectory() as d:
            r1, r2 = two_rounds(d)
            # screen the change on the buyers who passed for already-paid in r1: b03 and b06
            for name in ("answers.jsonl", "scores.jsonl"):
                kept = [x for x in lines(os.path.join(r2, name)) if x["buyer_id"] in ("b03", "b06")]
                write(r2, name, jsonl(kept))
            result, code = run_json("diff", r1, r2)
        self.assertEqual(code, 0, result)
        self.assertEqual(result["buyers"], {"both": 2, "only_before": ["b01", "b02", "b04", "b05", "b07"],
                                            "only_after": []})
        self.assertEqual(result["flips"], {"pass_to_buy": ["b03"], "buy_to_pass": []})
        share = result["buy_share"]
        # 0 of 2 before; 1 of 2 after, b03 at intent 5: 0.75 / 2
        self.assertEqual((share["before"]["raw"], share["after"]["raw"]), (0, 0.5))
        self.assertEqual(share["after"]["discounted"], 0.375)
        self.assertEqual([r["buyer_id"] for r in result["rows"]], ["b03", "b06"])


class CompetitorAdded(unittest.TestCase):
    def test_an_option_new_in_the_later_round_is_counted_and_switched_to(self):
        with tempfile.TemporaryDirectory() as d:
            r1, r2 = two_rounds(d)
            with open(os.path.join(r2, "round.json"), encoding="utf-8") as f:
                meta = json.load(f)
            meta["options"].append("Clockify")
            write(r2, "round.json", json.dumps(meta))
            answers = lines(os.path.join(r2, "answers.jsonl"))
            for a in answers:
                a["options"].append("Clockify")
            answers[5]["choice"] = "Clockify"                       # b06 takes the newcomer instead of Toggl
            write(r2, "answers.jsonl", jsonl(answers))
            result, code = run_json("diff", r1, r2)
        self.assertEqual(code, 0, result)
        self.assertEqual(result["choices"][-2:], [{"option": "nothing", "before": 2, "after": 3},
                                                  {"option": "Clockify", "before": 0, "after": 1}])
        self.assertEqual(result["choices"][1], {"option": "Toggl", "before": 1, "after": 0})
        self.assertIn({"buyer_id": "b06", "from": "Harvest", "to": "Clockify"}, result["switches"])


def set_round(round_dir, **fields):
    """Rewrite round.json with fields replaced (None removes one)."""
    with open(os.path.join(round_dir, "round.json"), encoding="utf-8") as f:
        meta = json.load(f)
    meta.update(fields)
    write(round_dir, "round.json", json.dumps({k: v for k, v in meta.items() if v is not None}))


class PricePeriod(unittest.TestCase):
    """A change from per month to per booking moves the card's unit, not just its number: prices in two units
    are never subtracted."""

    def test_a_period_must_be_text(self):
        with tempfile.TemporaryDirectory() as d:
            r1, _ = two_rounds(d)
            set_round(r1, period=1)
            result, code = run_json("validate", os.path.join(r1, "round.json"))
        self.assertEqual((code, [e["field"] for e in result[0]["errors"]]), (3, ["period"]))

    def test_rounds_in_the_same_period_compare_prices(self):
        with tempfile.TemporaryDirectory() as d:
            r1, r2 = two_rounds(d)
            set_round(r1, period="month")
            set_round(r2, period="month", price=12)
            result, _ = run_json("diff", r1, r2)
            text = run("diff", r1, r2).stdout
        price = result["price"]
        self.assertEqual((price["card"]["change"], price["mixed"]), (3, None))
        self.assertEqual((result["before"]["period"], result["after"]["period"]), ("month", "month"))
        self.assertIn("Card price 9 -> 12 EUR per month;", text)

    def test_prices_in_another_period_are_not_compared(self):
        with tempfile.TemporaryDirectory() as d:
            r1, r2 = two_rounds(d)
            set_round(r1, period="month")
            set_round(r2, period="booking", price=1.5)
            result, code = run_json("diff", r1, r2)
            text = run("diff", r1, r2).stdout
        self.assertEqual(code, 0, result)
        price = result["price"]
        self.assertEqual(price["mixed"], "r1 is priced in EUR per month, r2 in EUR per booking")
        self.assertEqual((price["card"]["change"], price["range_change"], price["optimal_change"],
                          price["indifference_change"]), (None, None, None, None))
        self.assertEqual(result["flips"], {"pass_to_buy": ["b03"], "buy_to_pass": ["b02"]})   # buyers still compared
        self.assertNotIn("9 -> 1.5", text)
        self.assertIn("Prices not compared: r1 is priced in EUR per month, r2 in EUR per booking", text)

    def test_a_period_stated_on_one_round_only_is_mixed(self):
        with tempfile.TemporaryDirectory() as d:
            r1, r2 = two_rounds(d)
            set_round(r2, period="booking")
            result, _ = run_json("diff", r1, r2)
        self.assertEqual(result["price"]["mixed"], "r1 is priced in EUR with no period stated, r2 in EUR per booking")
        self.assertIsNone(result["price"]["card"]["change"])


class Refused(unittest.TestCase):
    def test_rounds_of_two_panels_are_not_compared(self):
        with tempfile.TemporaryDirectory() as d:
            r1, _ = two_rounds(os.path.join(d, "one"))
            _, other = two_rounds(os.path.join(d, "two"))
            out = run("diff", r1, other)
        self.assertEqual(out.returncode, 2)
        self.assertIn("same buyers", out.stderr)

    def test_an_invalid_record_in_either_round_stops_the_diff(self):
        with tempfile.TemporaryDirectory() as d:
            r1, r2 = two_rounds(d)
            scores = lines(os.path.join(r2, "scores.jsonl"))
            scores[2]["intent"] = 7
            write(r2, "scores.jsonl", jsonl(scores))
            result, code = run_json("diff", r1, r2)
        self.assertEqual(code, 3)
        self.assertEqual([(e["line"], e["field"]) for e in result["errors"]], [(3, "intent")])
        self.assertTrue(result["errors"][0]["file"].endswith("scores.jsonl"))


if __name__ == "__main__":
    unittest.main()
