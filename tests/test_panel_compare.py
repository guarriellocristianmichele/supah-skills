"""Tests for skills/buyer-panel/scripts/panel.py split, compare and competitor. Run: python -m unittest discover -s tests"""
import json
import os
import shutil
import tempfile
import unittest

from test_panel import FIXTURES, NORMAL, jsonl, lines, run, run_json, write

OPTIONS = "offer,Toggl,Harvest,nothing"


def nine_buyers(d):
    """Three segments of three buyers each: every segment has one buyer left over after pairing."""
    base = lines(os.path.join(NORMAL, "buyers.jsonl"))[0]
    buyers = [dict(base, id=f"n{i}{j}", name=f"Buyer {i}{j}", segment=f"seg{i}") for i in (1, 2, 3) for j in (1, 2, 3)]
    return write(d, "buyers.jsonl", jsonl(buyers))


class Split(unittest.TestCase):
    """The normal panel: solo b01 b02, studio b03 b04, agency b05 b06, school b07."""

    def split(self, d, buyers, seed="7"):
        a, b = os.path.join(d, "a", "cards.jsonl"), os.path.join(d, "b", "cards.jsonl")
        os.makedirs(os.path.dirname(a), exist_ok=True)
        os.makedirs(os.path.dirname(b), exist_ok=True)
        result, code = run_json("split", "--buyers", buyers, "--options", OPTIONS, "--batch-size", "2",
                                "--seed", seed, "--out-a", a, "--out-b", b)
        return result, code, lines(a), lines(b)

    def test_each_segment_is_halved_and_each_buyer_sees_one_side(self):
        with tempfile.TemporaryDirectory() as d:
            result, code, a, b = self.split(d, os.path.join(NORMAL, "buyers.jsonl"))
        self.assertEqual(code, 0, result)
        ids_a, ids_b = {c["buyer_id"] for c in a}, {c["buyer_id"] for c in b}
        self.assertEqual(ids_a | ids_b, {"b01", "b02", "b03", "b04", "b05", "b06", "b07"})
        self.assertEqual(ids_a & ids_b, set())
        # one of each pair per side; the school buyer, alone in its segment, goes to A (the first left over)
        for pair in (("b01", "b02"), ("b03", "b04"), ("b05", "b06")):
            self.assertEqual(len(ids_a & set(pair)), 1, pair)
        self.assertIn("b07", ids_a)
        self.assertEqual(result["segments"], [{"segment": "solo", "a": 1, "b": 1}, {"segment": "studio", "a": 1, "b": 1},
                                              {"segment": "agency", "a": 1, "b": 1},
                                              {"segment": "school", "a": 1, "b": 0}])
        self.assertEqual((result["a"]["buyers"], result["b"]["buyers"]), (4, 3))

    def test_left_over_buyers_alternate_sides_so_the_halves_stay_even(self):
        with tempfile.TemporaryDirectory() as d:
            result, code, a, b = self.split(d, nine_buyers(d))
        self.assertEqual(code, 0, result)
        # seg1's spare to A, seg2's to B, seg3's to A: 2+1+2 and 1+2+1
        self.assertEqual(result["segments"], [{"segment": "seg1", "a": 2, "b": 1}, {"segment": "seg2", "a": 1, "b": 2},
                                              {"segment": "seg3", "a": 2, "b": 1}])
        self.assertEqual((len(a), len(b)), (5, 4))

    def test_cards_are_dealt_per_half_in_batches_mixed_across_segments(self):
        with tempfile.TemporaryDirectory() as d:
            result, _, a, b = self.split(d, os.path.join(NORMAL, "buyers.jsonl"))
        segment = {x["id"]: x["segment"] for x in lines(os.path.join(NORMAL, "buyers.jsonl"))}
        for cards in (a, b):
            for c in cards:
                self.assertEqual(sorted(c["options"]), sorted(OPTIONS.split(",")))
            # batches of 2 numbered from 1 in each half, and the first batch holds two segments
            self.assertEqual([c["batch"] for c in cards], [1, 1, 2, 2][:len(cards)] + [3] * max(0, len(cards) - 4))
            self.assertEqual(len({segment[c["buyer_id"]] for c in cards[:2]}), 2)
        self.assertEqual((result["a"]["batches"], result["b"]["batches"], result["seed"]), (2, 2, 7))

    def test_the_same_seed_splits_the_same_way(self):
        with tempfile.TemporaryDirectory() as d:
            first = self.split(d, nine_buyers(d))[2:]
            second = self.split(d, nine_buyers(d))[2:]
            other = self.split(d, nine_buyers(d), seed="8")[2:]
        self.assertEqual(first, second)
        self.assertNotEqual(first, other)

    def test_options_without_nothing_are_refused(self):
        with tempfile.TemporaryDirectory() as d:
            out = run("split", "--buyers", os.path.join(NORMAL, "buyers.jsonl"), "--options", "offer,Toggl",
                      "--out-a", os.path.join(d, "a.jsonl"), "--out-b", os.path.join(d, "b.jsonl"))
        self.assertEqual(out.returncode, 2)


def two_halves(d):
    """The normal panel with the compare fixture's r2-A (b01 b03 b05 b07, the r1 offer) and r2-B (b02 b04 b06,
    the offer positioned for studios that quote by project); returns the two round folders."""
    panel = os.path.join(d, "panel")
    shutil.copytree(NORMAL, panel)
    shutil.copytree(os.path.join(FIXTURES, "compare"), panel, dirs_exist_ok=True)
    return os.path.join(panel, "rounds", "r2-A"), os.path.join(panel, "rounds", "r2-B")


class Compare(unittest.TestCase):
    """Expected values worked by hand from the two half rounds."""

    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as d:
            a, b = two_halves(d)
            cls.result, cls.code = run_json("compare", a, b)
            cls.text = run("compare", a, b)

    def test_conversion_on_each_side(self):
        self.assertEqual(self.code, 0, self.result)
        a, b = self.result["a"], self.result["b"]
        self.assertEqual((a["label"], a["variant"], b["label"], b["variant"]), ("r2-A", "A", "r2-B", "B"))
        # A: b01 buys at intent 5, 0.75 / 4; B: b02 at 4 and b04 at 5, (0.25 + 0.75) / 3
        self.assertEqual((a["buyers"], a["buy"], a["raw"], a["discounted"]), (4, 1, 0.25, 0.1875))
        self.assertEqual((b["buyers"], b["buy"], b["raw"], b["discounted"]), (3, 2, 0.6667, 0.3333))
        self.assertEqual(self.result["scheme"], "top-box 75/25/10/5/2 (Jamieson and Bass 1989)")

    def test_reasons_and_choices_on_each_side(self):
        a, b = self.result["a"], self.result["b"]
        self.assertEqual(a["pass_reasons"], [{"reason": "no-need", "count": 2}, {"reason": "already-paid", "count": 1}])
        self.assertEqual(a["buy_reasons"], [{"reason": "saves-time", "count": 1}])
        self.assertEqual(b["pass_reasons"], [{"reason": "already-paid", "count": 1}])
        self.assertEqual(b["buy_reasons"], [{"reason": "better-quotes", "count": 1}, {"reason": "saves-time", "count": 1}])
        self.assertEqual(a["choices"], [{"option": "offer", "count": 1}, {"option": "Toggl", "count": 1},
                                        {"option": "Harvest", "count": 0}, {"option": "nothing", "count": 2}])
        self.assertEqual(b["choices"], [{"option": "offer", "count": 2}, {"option": "Toggl", "count": 0},
                                        {"option": "Harvest", "count": 1}, {"option": "nothing", "count": 0}])

    def test_difference_with_the_panels_noise_beside_it(self):
        diff, noise = self.result["difference"], self.result["noise"]
        # raw 2/3 - 1/4 = 5/12; discounted 1/3 - 3/16 = 7/48
        self.assertEqual((diff["raw"], diff["discounted"]), (0.4167, 0.1458))
        # pooled 3 of 7: sqrt(3/7 * 4/7 * (1/4 + 1/3)) = sqrt(1/7); one buyer moves the smaller side by 1/3
        self.assertEqual((noise["standard_error"], noise["one_buyer"]), (0.378, 0.3333))
        # noise is shown, not tested: no verdict on which side converts more
        self.assertNotIn("within_noise", self.result)
        self.assertNotIn("higher", self.result)

    def test_halves_balanced_by_segment(self):
        self.assertEqual(self.result["segments"], [{"segment": "solo", "a": 1, "b": 1},
                                                   {"segment": "studio", "a": 1, "b": 1},
                                                   {"segment": "agency", "a": 1, "b": 1},
                                                   {"segment": "school", "a": 1, "b": 0}])
        self.assertTrue(self.result["balanced"])

    def test_text_output_is_the_reports_comparison(self):
        out = self.text
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("A r2-A: BUY 1 of 4, raw 25.0%, discounted 18.8%", out.stdout)
        self.assertIn("B r2-B: BUY 2 of 3, raw 66.7%, discounted 33.3%", out.stdout)
        self.assertIn("B minus A: raw +41.7 points, discounted +14.6 points. Noise: one standard error is 37.8 points, "
                      "and one buyer moves the smaller side by 33.3 points. Noise is shown, not tested: a difference "
                      "near the noise or the one-buyer swing may be no difference.", out.stdout)
        self.assertNotIn("twice", out.stdout)
        self.assertIn("Segments (A/B): solo 1/1, studio 1/1, agency 1/1, school 1/0", out.stdout)
        self.assertIn("Top reasons to pass: A no-need 2, already-paid 1; B already-paid 1", out.stdout)


class CompareMissing(unittest.TestCase):
    def test_a_half_buyer_without_a_scored_answer_is_named(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = two_halves(d)
            for name in ("answers.jsonl", "scores.jsonl"):
                write(b, name, jsonl([x for x in lines(os.path.join(b, name)) if x["buyer_id"] != "b02"]))
            result, code = run_json("compare", a, b)
            text = run("compare", a, b).stdout
        self.assertEqual(code, 0, result)
        # b02 was dealt a card for B but never answered; the other half's buyers are not missing from B
        self.assertEqual((result["a"]["missing"], result["b"]["missing"]), ([], ["b02"]))
        self.assertEqual(result["b"]["buyers"], 2)
        self.assertIn("Missing in B r2-B (dealt a card, no scored answer): b02", text)


class CompareRefused(unittest.TestCase):
    def test_a_buyer_who_saw_both_variants_stops_the_comparison(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = two_halves(d)
            answers = lines(os.path.join(a, "answers.jsonl"))[:1]
            scores = lines(os.path.join(a, "scores.jsonl"))[:1]
            write(b, "answers.jsonl", jsonl(lines(os.path.join(b, "answers.jsonl")) + [dict(answers[0], round="r2-B")]))
            write(b, "scores.jsonl", jsonl(lines(os.path.join(b, "scores.jsonl")) + [dict(scores[0], round="r2-B")]))
            out = run("compare", a, b)
        self.assertEqual(out.returncode, 2)
        self.assertIn("b01", out.stderr)

    def test_rounds_of_two_panels_are_not_compared(self):
        with tempfile.TemporaryDirectory() as d:
            a, _ = two_halves(os.path.join(d, "one"))
            _, b = two_halves(os.path.join(d, "two"))
            out = run("compare", a, b)
        self.assertEqual(out.returncode, 2)

    def test_an_invalid_record_stops_the_comparison(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = two_halves(d)
            scores = lines(os.path.join(b, "scores.jsonl"))
            scores[1]["intent"] = 0
            write(b, "scores.jsonl", jsonl(scores))
            result, code = run_json("compare", a, b)
        self.assertEqual(code, 3)
        self.assertEqual([(e["line"], e["field"]) for e in result["errors"]], [(2, "intent")])


def with_competitor(d):
    """The normal panel with the competitor fixture's r2: the same seven buyers, Clockify added at 4 EUR."""
    panel = os.path.join(d, "panel")
    shutil.copytree(NORMAL, panel)
    shutil.copytree(os.path.join(FIXTURES, "competitor"), panel, dirs_exist_ok=True)
    return os.path.join(panel, "rounds", "r1"), os.path.join(panel, "rounds", "r2")


def repriced(r2):
    """r3: r2 again with Clockify at 8 EUR instead of 4; b06 goes back to Harvest, everyone else answers as in r2."""
    r3 = os.path.join(os.path.dirname(r2), "r3")
    os.makedirs(r3)
    with open(os.path.join(r2, "round.json"), encoding="utf-8") as f:
        meta = json.load(f)
    meta.update(label="r3", base="r2", competitor={"name": "Clockify", "price": 8, "was": 4})
    write(r3, "round.json", json.dumps(meta))
    answers = [dict(a, round="r3") for a in lines(os.path.join(r2, "answers.jsonl"))]
    scores = [dict(s, round="r3") for s in lines(os.path.join(r2, "scores.jsonl"))]
    answers[5].update(reaction="At eight a seat Clockify saves nothing over Harvest, which is paid through next year.",
                      choice="Harvest")
    scores[5].update(intent=2, reason="already-paid", quote="Harvest, which is paid through next year")
    write(r3, "answers.jsonl", jsonl(answers))
    write(r3, "scores.jsonl", jsonl(scores))
    return r3


class CompetitorAdded(unittest.TestCase):
    """r1 is the normal round; r2 adds Clockify at 4 EUR. Expected values worked by hand from the two rounds."""

    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as d:
            r1, r2 = with_competitor(d)
            cls.result, cls.code = run_json("competitor", r1, r2)
            cls.text = run("competitor", r1, r2)

    def test_the_round_diff_is_all_there(self):
        self.assertEqual(self.code, 0, self.result)
        # b02 left the offer for Clockify; b06 left Harvest for it
        self.assertEqual(self.result["flips"], {"pass_to_buy": [], "buy_to_pass": ["b02"]})
        self.assertEqual(self.result["switches"], [{"buyer_id": "b02", "from": "offer", "to": "Clockify"},
                                                   {"buyer_id": "b06", "from": "Harvest", "to": "Clockify"}])
        self.assertEqual(self.result["choices"][-1], {"option": "Clockify", "before": 0, "after": 2})
        # BUY 3 -> 2 of 7; discounted 1.10 -> 0.75 + 0.10 = 0.85
        self.assertEqual(self.result["buy_share"]["raw_change"], -0.1429)
        self.assertEqual(self.result["buy_share"]["discounted_change"], -0.0357)

    def test_the_competitor_and_what_changed_for_it(self):
        c = self.result["competitor"]
        self.assertEqual((c["name"], c["change"], c["price"]), ("Clockify", "added", {"before": None, "after": 4}))
        self.assertEqual(c["chosen"], {"before": 0, "after": 2})

    def test_who_switched_to_it_and_why(self):
        c = self.result["competitor"]
        self.assertEqual(c["switched_to"], [
            {"buyer_id": "b02", "from": "offer", "reason": "cheaper-elsewhere",
             "quote": "Four euros for Clockify against nine"},
            {"buyer_id": "b06", "from": "Harvest", "reason": "cheaper-elsewhere",
             "quote": "Clockify at four for twenty people is a saving"}])
        self.assertEqual((c["left"], c["other_switches"]), ([], []))

    def test_who_stayed_and_the_reasons_that_held_them(self):
        self.assertEqual(self.result["competitor"]["stayed"], [
            {"option": "offer", "buyers": ["b01", "b04"],
             "reasons": [{"reason": "better-quotes", "count": 1}, {"reason": "saves-time", "count": 1}]},
            {"option": "Toggl", "buyers": ["b03"], "reasons": [{"reason": "already-paid", "count": 1}]},
            {"option": "nothing", "buyers": ["b05", "b07"], "reasons": [{"reason": "no-need", "count": 2}]}])

    def test_text_output_is_the_diff_then_the_competitor(self):
        out = self.text
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("r1 -> r2: 7 buyers in both rounds", out.stdout)
        self.assertIn("Clockify added at 4 EUR: chosen by 0 -> 2 buyers.", out.stdout)
        self.assertIn("Switched to Clockify: b02 from offer (cheaper-elsewhere: \"Four euros for Clockify against "
                      "nine\"); b06 from Harvest (cheaper-elsewhere: \"Clockify at four for twenty people is a "
                      "saving\")", out.stdout)
        self.assertIn("Left Clockify: none", out.stdout)
        self.assertIn("Stayed: offer b01, b04 (better-quotes 1, saves-time 1); Toggl b03 (already-paid 1); "
                      "nothing b05, b07 (no-need 2)", out.stdout)
        self.assertLess(out.stdout.index("| b07 Mira Novak"), out.stdout.index("Clockify added"))


class CompetitorRepriced(unittest.TestCase):
    def test_a_price_rise_shows_who_left_it_and_who_it_kept(self):
        with tempfile.TemporaryDirectory() as d:
            _, r2 = with_competitor(d)
            r3 = repriced(r2)
            result, code = run_json("competitor", r2, r3)
        self.assertEqual(code, 0, result)
        c = result["competitor"]
        self.assertEqual((c["change"], c["price"], c["chosen"]),
                         ("repriced", {"before": 4, "after": 8}, {"before": 2, "after": 1}))
        self.assertEqual(c["switched_to"], [])
        self.assertEqual(c["left"], [{"buyer_id": "b06", "to": "Harvest", "reason": "already-paid",
                                      "quote": "Harvest, which is paid through next year"}])
        self.assertIn({"option": "Clockify", "buyers": ["b02"], "reasons": [{"reason": "cheaper-elsewhere", "count": 1}]},
                      c["stayed"])


class CompetitorRefused(unittest.TestCase):
    def test_a_round_that_names_no_competitor(self):
        with tempfile.TemporaryDirectory() as d:
            r1, r2 = with_competitor(d)
            with open(os.path.join(r2, "round.json"), encoding="utf-8") as f:
                meta = json.load(f)
            del meta["competitor"]
            write(r2, "round.json", json.dumps(meta))
            out = run("competitor", r1, r2)
        self.assertEqual(out.returncode, 2)
        self.assertIn("competitor", out.stderr)

    def test_a_repriced_competitor_must_say_its_old_price(self):
        with tempfile.TemporaryDirectory() as d:
            _, r2 = with_competitor(d)
            r3 = repriced(r2)
            with open(os.path.join(r3, "round.json"), encoding="utf-8") as f:
                meta = json.load(f)
            del meta["competitor"]["was"]
            write(r3, "round.json", json.dumps(meta))
            out = run("competitor", r2, r3)
        self.assertEqual(out.returncode, 2)
        self.assertIn("was", out.stderr)

    def test_the_competitor_must_be_one_of_the_options_shown(self):
        with tempfile.TemporaryDirectory() as d:
            _, r2 = with_competitor(d)
            with open(os.path.join(r2, "round.json"), encoding="utf-8") as f:
                meta = json.load(f)
            bad = dict(meta, competitor={"name": "Clockfy", "price": 4})
            reserved = dict(meta, competitor={"name": "nothing", "price": -1})
            paths = [write(os.path.join(d, "x"), "round.json", json.dumps(bad)),
                     write(os.path.join(d, "y"), "round.json", json.dumps(reserved))]
            result, code = run_json("validate", *paths)
        self.assertEqual(code, 3)
        self.assertEqual([e["field"] for e in result[0]["errors"]], ["competitor.name"])
        self.assertEqual(sorted(e["field"] for e in result[1]["errors"]), ["competitor.name", "competitor.price"])


class BriefAlternatives(unittest.TestCase):
    """An alternative sold abroad is priced in its own currency and period, stated beside its price."""

    def brief(self, d, brief_period="month", **alt):
        with open(os.path.join(NORMAL, "brief.json"), encoding="utf-8") as f:
            rec = json.load(f)
        rec["alternatives"][0].update(alt)
        return write(d, "brief.json", json.dumps(dict(rec, period=brief_period)))

    def test_the_brief_price_period_is_text(self):
        with tempfile.TemporaryDirectory() as d:
            result, code = run_json("validate", self.brief(d, brief_period=" "))
        self.assertEqual((code, [e["field"] for e in result[0]["errors"]]), (3, ["period"]))

    def test_an_alternative_states_its_currency_and_period(self):
        with tempfile.TemporaryDirectory() as d:
            result, code = run_json("validate", self.brief(d, currency="USD", period="user per month"))
        self.assertEqual((code, result[0]["errors"]), (0, []))

    def test_a_currency_or_period_that_is_not_text_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            result, code = run_json("validate", self.brief(d, currency=10, period=""))
        self.assertEqual(code, 3)
        self.assertEqual(sorted(e["field"] for e in result[0]["errors"]),
                         ["alternatives[0].currency", "alternatives[0].period"])


if __name__ == "__main__":
    unittest.main()
