"""Tests for skills/buyer-panel/scripts/panel.py quotes (pitch mode). Run: python -m unittest discover -s tests"""
import os
import unittest

import test_panel as tp

R1 = os.path.join(tp.NORMAL, "rounds", "r1")


class MostLikelyType(unittest.TestCase):
    def test_picks_the_type_most_likely_to_buy_and_traces_quotes_to_buyers(self):
        # solo: b01 BUY intent 5, b02 BUY intent 4 -> discounted (0.75 + 0.25) / 2 = 0.5, ahead of studio's 0.05
        result, code = tp.run_json("quotes", R1, "--seed", "1")
        self.assertEqual(code, 0)
        self.assertEqual(result["type"], "solo")
        self.assertEqual(result["picked"], "most likely")
        quoted = {q["buyer_id"] for q in result["quotes"]}
        held = {h["buyer_id"] for h in result["holdout"]}
        self.assertEqual(quoted | held, {"b01", "b02"})
        self.assertEqual((len(quoted), len(held)), (1, 1))
        words = {"b01": "I stop losing Friday afternoons to my sheet",
                 "b02": "a tracker that starts on its own is the point"}
        for q in result["quotes"]:
            self.assertEqual(q["quote"], words[q["buyer_id"]])


class NamedType(unittest.TestCase):
    def test_a_named_type_keeps_its_buyer_in_the_quotes_and_holds_out_the_one_who_passed(self):
        # studio: b04 BUY (intent 3), b03 PASS for Toggl (intent 2); the BUY is dealt to the quotes first
        for seed in ("1", "2", "3"):
            result, code = tp.run_json("quotes", R1, "--type", "studio", "--seed", seed)
            self.assertEqual(code, 0)
            self.assertEqual((result["type"], result["picked"]), ("studio", "named"))
            self.assertEqual([(q["buyer_id"], q["quote"]) for q in result["quotes"]],
                             [("b04", "knowing where hours go would help me quote better")])
            self.assertEqual([(h["buyer_id"], h["decision"], h["choice"], h["intent"]) for h in result["holdout"]],
                             [("b03", "PASS", "Toggl", 2)])

    def test_a_quote_missing_from_the_reaction_stops_extraction(self):
        with tp.tempfile.TemporaryDirectory() as d:
            r1 = tp.copy_round(d)
            scores = tp.lines(os.path.join(r1, "scores.jsonl"))
            scores[0]["quote"] = "best tracker I have ever seen"
            tp.write(r1, "scores.jsonl", tp.jsonl(scores))
            result, code = tp.run_json("quotes", r1)
        self.assertEqual(code, 3)
        self.assertEqual([(e["field"], e["line"]) for e in result["errors"]], [("quote", 1)])

    def test_an_unknown_type_is_bad_usage(self):
        out = tp.run("quotes", R1, "--type", "enterprise")
        self.assertEqual(out.returncode, 2)
        self.assertIn("enterprise", out.stderr)
        self.assertIn("solo", out.stderr)


PITCH_R1 = os.path.join(tp.FIXTURES, "pitch", "rounds", "r1")
STUDIO_BUY, STUDIO_PASS = {"b01", "b02"}, {"b03", "b04"}


class Holdout(unittest.TestCase):
    def test_half_the_type_is_held_out_with_one_buyer_and_one_passer_on_each_side(self):
        # studio in the pitch fixture: b01 BUY 5, b02 BUY 4, b03 PASS 2, b04 PASS 1
        for seed in ("1", "2", "3", "4"):
            result, code = tp.run_json("quotes", PITCH_R1, "--seed", seed)
            self.assertEqual(code, 0)
            self.assertEqual(result["type"], "studio")
            quoted = {q["buyer_id"] for q in result["quotes"]}
            held = {h["buyer_id"] for h in result["holdout"]}
            self.assertEqual(quoted | held, STUDIO_BUY | STUDIO_PASS)
            self.assertEqual(len(held & STUDIO_BUY), 1)
            self.assertEqual(len(held & STUDIO_PASS), 1)

    def test_the_held_out_buyers_first_round_is_reported(self):
        result, _ = tp.run_json("quotes", PITCH_R1, "--seed", "1")
        first = result["first_round"]
        self.assertEqual((first["buyers"], first["buy"], first["raw"]), (2, 1, 0.5))
        # the held-out BUY is b01 (0.75 / 2) or b02 (0.25 / 2); the held-out PASS adds nothing
        held_buy = ({h["buyer_id"] for h in result["holdout"]} & STUDIO_BUY).pop()
        self.assertEqual(first["discounted"], {"b01": 0.375, "b02": 0.125}[held_buy])

    def test_the_held_out_buyers_words_never_reach_the_output(self):
        words = {"b01": "Friday chase", "b02": "less of a guess", "b03": "paid for the year",
                 "b04": "reach the invoice"}
        for seed in ("1", "2"):
            out = tp.run("--json", "quotes", PITCH_R1, "--seed", seed)
            held = {h["buyer_id"] for h in tp.json.loads(out.stdout)["holdout"]}
            for bid in held:
                self.assertNotIn(words[bid], out.stdout)

    def test_the_same_seed_holds_out_the_same_buyers(self):
        first, _ = tp.run_json("quotes", PITCH_R1, "--seed", "7")
        again, _ = tp.run_json("quotes", PITCH_R1, "--seed", "7")
        self.assertEqual(first["holdout"], again["holdout"])
        self.assertEqual(first["seed"], 7)

    def test_holdout_size_can_be_set_up_to_half_the_type(self):
        result, code = tp.run_json("quotes", PITCH_R1, "--holdout", "1", "--seed", "1")
        self.assertEqual(code, 0)
        self.assertEqual(len(result["holdout"]), 1)
        self.assertEqual(len(result["quotes"]), 3)
        self.assertEqual(tp.run("quotes", PITCH_R1, "--holdout", "3").returncode, 2)

    def test_the_held_out_buyers_are_written_as_a_buyers_file_for_the_try_out(self):
        with tp.tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "buyers.jsonl")
            result, code = tp.run_json("quotes", PITCH_R1, "--seed", "1", "--holdout-out", path)
            self.assertEqual(code, 0)
            written = tp.lines(path)
            self.assertEqual([b["id"] for b in written], [h["buyer_id"] for h in result["holdout"]])
            self.assertEqual({b["segment"] for b in written}, {"studio"})
            self.assertEqual(tp.run_json("validate", path)[1], 0)


if __name__ == "__main__":
    unittest.main()
