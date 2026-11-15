"""Tests for skills/buyer-panel/scripts/panel.py, mode ground. Run: python -m unittest discover -s tests"""
import json
import os
import shutil
import tempfile
import unittest

from test_panel import FIXTURES, NORMAL, jsonl, lines, run, run_json, write

GROUND = os.path.join(FIXTURES, "ground")
SMOKE = os.path.join(GROUND, "real", "smoke-1.json")


def real(d, name, **fields):
    """A real-results file in d/real/, from the smoke-1 fixture with fields replaced (None removes one)."""
    with open(SMOKE, encoding="utf-8") as f:
        rec = json.load(f)
    rec.update(fields)
    rec = {k: v for k, v in rec.items() if v is not None}
    return write(d, os.path.join("real", name + ".json"), json.dumps(rec))


class ValidateReal(unittest.TestCase):
    def test_smoke_test_results_pass(self):
        result, code = run_json("validate", SMOKE)
        self.assertEqual(code, 0, result)
        self.assertEqual((result[0]["kind"], result[0]["records"]), ("real", 1))

    def test_results_that_cannot_be_compared_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            files = [
                real(d, "a", test="survey"),                                 # not a real test the skill knows
                real(d, "b", conversions=401),                               # more conversions than visits
                real(d, "c", visits=0),                                      # nobody reached
                real(d, "d", conversions=None),                              # count missing
                real(d, "e", date="20 November"),                            # not a date
                real(d, "f", test="interviews", visits=None, conversions=None, interviews=5, commitments=2.5),
            ]
            result, code = run_json("validate", *files)
        self.assertEqual(code, 3)
        fields = [sorted(e["field"] for e in r["errors"]) for r in result]
        self.assertEqual(fields, [["test"], ["conversions"], ["visits"], ["conversions"], ["date"], ["commitments"]])


    def test_dates_are_written_yyyy_mm_dd_on_every_python(self):
        # Python 3.11 and later read 20261120 and 2026-W47-5 as dates; 3.10 and the schema do not
        with tempfile.TemporaryDirectory() as d:
            files = [real(d, "a", date="20261120"), real(d, "b", date="2026-W47-5")]
            result, code = run_json("validate", *files)
        self.assertEqual(code, 3)
        self.assertEqual([[e["field"] for e in r["errors"]] for r in result], [["date"], ["date"]])


def panel_with(d, *reals):
    """A writable copy of the normal panel with real-results files in its real/ folder; returns the panel."""
    panel = os.path.join(d, "panel")
    shutil.copytree(NORMAL, panel)
    for name, fields in reals:
        real(panel, name, **fields)
    return panel


class Ground(unittest.TestCase):
    """Round r1 of the normal fixture: 3 of 7 chose the offer, intents 5, 4, 3 weigh 1.10, discounted 1.10 / 7."""

    def test_smoke_test_ratio_is_stored_in_the_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            panel = panel_with(d, ("smoke-1", {}))
            result, code = run_json("ground", os.path.join(panel, "real", "smoke-1.json"))
            stored = lines(os.path.join(d, "grounding.jsonl"))              # the project's ledger, beside the panels
            in_panel = os.path.exists(os.path.join(panel, "grounding.jsonl"))
        self.assertEqual(code, 0, result)
        self.assertFalse(in_panel)
        self.assertEqual(result["panel"], "panel")
        # 22 of 400 visits converted: 0.055; 0.055 / (1.10 / 7) = 0.385 / 1.10 = 0.35
        self.assertEqual(result["real"], {"reached": 400, "acted": 22, "rate": 0.055, "measure": "conversions per visit"})
        self.assertAlmostEqual(result["predicted"]["raw"], 0.4286, places=4)
        self.assertAlmostEqual(result["predicted"]["discounted"], 0.1571, places=4)
        self.assertEqual(result["ratio"], 0.35)
        self.assertEqual((result["label"], result["test"], result["round"], result["date"]),
                         ("smoke-1", "smoke-test", "r1", "2026-11-20"))
        self.assertTrue(result["offer"].startswith("Tickr: a time tracker"))
        self.assertEqual(stored, [result])

    def test_interviews_that_beat_the_panel_give_a_ratio_above_one(self):
        with tempfile.TemporaryDirectory() as d:
            panel = panel_with(d, ("talks-1", {"label": "talks-1", "test": "interviews", "visits": None,
                                               "conversions": None, "interviews": 5, "commitments": 1}))
            result, code = run_json("ground", os.path.join(panel, "real", "talks-1.json"))
        self.assertEqual(code, 0, result)
        # 1 of 5: 0.2; 0.2 / (1.10 / 7) = 1.4 / 1.10 = 1.2727
        self.assertEqual(result["real"]["rate"], 0.2)
        self.assertEqual(result["real"]["measure"], "commitments per interview")
        self.assertEqual(result["ratio"], 1.2727)

    def test_importing_the_same_results_again_replaces_their_line(self):
        with tempfile.TemporaryDirectory() as d:
            panel = panel_with(d, ("smoke-1", {}), ("talks-1", {"label": "talks-1", "test": "interviews",
                                                                "visits": None, "conversions": None,
                                                                "interviews": 5, "commitments": 1}))
            run_json("ground", os.path.join(panel, "real", "smoke-1.json"))
            run_json("ground", os.path.join(panel, "real", "talks-1.json"))
            real(panel, "smoke-1", conversions=44)                     # corrected count, same label
            result, code = run_json("ground", os.path.join(panel, "real", "smoke-1.json"))
            stored = lines(os.path.join(d, "grounding.jsonl"))
        self.assertEqual(code, 0, result)
        self.assertEqual([(g["label"], g["real"]["acted"]) for g in stored], [("smoke-1", 44), ("talks-1", 1)])
        # 44 / 400 = 0.11, twice 0.055: 0.70
        self.assertEqual(stored[0]["ratio"], 0.7)

    def test_results_at_another_price_or_round_are_not_compared(self):
        with tempfile.TemporaryDirectory() as d:
            panel = panel_with(d, ("dear", {"label": "dear", "price": 12}), ("lost", {"label": "lost", "round": "r9"}))
            dear, dear_code = run_json("ground", os.path.join(panel, "real", "dear.json"))
            lost, lost_code = run_json("ground", os.path.join(panel, "real", "lost.json"))
            written = os.path.exists(os.path.join(d, "grounding.jsonl"))
        self.assertEqual((dear_code, lost_code), (3, 3))
        self.assertEqual([e["field"] for e in dear["errors"]], ["price"])
        self.assertEqual([e["field"] for e in lost["errors"]], ["round"])
        self.assertFalse(written)

    def test_a_round_nobody_bought_in_gives_no_ratio(self):
        with tempfile.TemporaryDirectory() as d:
            panel = panel_with(d, ("smoke-1", {}))
            r1 = os.path.join(panel, "rounds", "r1")
            answers = lines(os.path.join(r1, "answers.jsonl"))
            for a in answers:
                if a["choice"] == "offer":
                    a["choice"] = "nothing"
            write(r1, "answers.jsonl", jsonl(answers))
            result, code = run_json("ground", os.path.join(panel, "real", "smoke-1.json"))
        self.assertEqual(code, 3)
        self.assertIn("predicts no buyer", result["errors"][0]["problem"])


class ProjectLedger(unittest.TestCase):
    def test_the_same_label_in_two_panels_keeps_two_lines(self):
        with tempfile.TemporaryDirectory() as d:
            one = panel_with(d, ("smoke-1", {}))
            two = os.path.join(d, "other")
            shutil.copytree(one, two)
            run_json("ground", os.path.join(one, "real", "smoke-1.json"))
            run_json("ground", os.path.join(two, "real", "smoke-1.json"))
            stored = lines(os.path.join(d, "grounding.jsonl"))
        self.assertEqual([(g["panel"], g["label"]) for g in stored], [("panel", "smoke-1"), ("other", "smoke-1")])

    def test_a_later_panel_in_the_project_shows_the_corrected_figure(self):
        with tempfile.TemporaryDirectory() as d:
            grounded_panel = panel_with(d, ("smoke-1", {}))
            run_json("ground", os.path.join(grounded_panel, "real", "smoke-1.json"))
            later = os.path.join(d, "later")
            shutil.copytree(NORMAL, later)
            result, code = run_json("aggregate", os.path.join(later, "rounds", "r1"))
            text = run("aggregate", os.path.join(later, "rounds", "r1")).stdout
        self.assertEqual(code, 0, result)
        # the grounded panel's ratio, 0.35, on this panel's r1: 0.35 x 1.10 / 7 = 0.055
        self.assertEqual((result["corrected"]["panel"], result["corrected"]["figure"]), ("panel", 0.055))
        self.assertIn("grounding smoke-1 of panel panel", text)


def second_round(panel):
    """Round r2: r1 again, with the three buyers who chose the offer (b01, b02, b04) all at intent 5."""
    r1, r2 = os.path.join(panel, "rounds", "r1"), os.path.join(panel, "rounds", "r2")
    shutil.copytree(r1, r2)
    with open(os.path.join(r2, "round.json"), encoding="utf-8") as f:
        meta = json.load(f)
    write(r2, "round.json", json.dumps(dict(meta, label="r2")))
    answers = [dict(a, round="r2") for a in lines(os.path.join(r2, "answers.jsonl"))]
    scores = [dict(s, round="r2", intent=5 if s["buyer_id"] in ("b01", "b02", "b04") else s["intent"])
              for s in lines(os.path.join(r2, "scores.jsonl"))]
    write(r2, "answers.jsonl", jsonl(answers))
    write(r2, "scores.jsonl", jsonl(scores))
    return r2


TALKS = ("talks-1", {"label": "talks-1", "test": "interviews", "date": "2026-11-25", "visits": None,
                     "conversions": None, "interviews": 5, "commitments": 1})


class Corrected(unittest.TestCase):
    def test_no_grounding_no_corrected_figure(self):
        result, code = run_json("aggregate", os.path.join(NORMAL, "rounds", "r1"))
        self.assertEqual(code, 0)
        self.assertNotIn("corrected", result)
        self.assertNotIn("Corrected", run("aggregate", os.path.join(NORMAL, "rounds", "r1")).stdout)

    def test_later_round_shows_corrected_figure_naming_its_grounding(self):
        with tempfile.TemporaryDirectory() as d:
            panel = panel_with(d, ("smoke-1", {}))
            run_json("ground", os.path.join(panel, "real", "smoke-1.json"))
            r2 = second_round(panel)
            result, code = run_json("aggregate", r2)
            text = run("aggregate", r2).stdout
        self.assertEqual(code, 0, result)
        # r2: intents 5, 5, 5 weigh 2.25, discounted 2.25 / 7 = 0.3214; corrected 0.35 x 2.25 / 7 = 0.1125
        self.assertAlmostEqual(result["buy_share"]["discounted"], 0.3214, places=4)
        corrected = result["corrected"]
        self.assertEqual(corrected["figure"], 0.1125)
        self.assertEqual(corrected["ratio"], 0.35)
        self.assertEqual(corrected["measure"], "conversions per visit")
        self.assertEqual((corrected["grounding"], corrected["test"], corrected["round"], corrected["date"]),
                         ("smoke-1", "smoke-test", "r1", "2026-11-20"))
        self.assertEqual((corrected["reached"], corrected["acted"]), (400, 22))
        line = next(x for x in text.splitlines() if x.startswith("Corrected"))
        self.assertIn("grounding smoke-1", line)
        self.assertIn("22 of 400", line)
        # the corrected line sits right after the raw and discounted one
        self.assertTrue(text.splitlines()[1].startswith("Corrected"))

    def test_the_latest_grounding_is_the_one_applied(self):
        with tempfile.TemporaryDirectory() as d:
            panel = panel_with(d, TALKS, ("smoke-1", {}))
            run_json("ground", os.path.join(panel, "real", "talks-1.json"))    # 2026-11-25, written first
            run_json("ground", os.path.join(panel, "real", "smoke-1.json"))    # 2026-11-20, written second
            result, code = run_json("aggregate", os.path.join(panel, "rounds", "r1"))
        self.assertEqual(code, 0, result)
        # talks-1 is the later test: 1.2727 x 1.10 / 7 = 0.2000
        self.assertEqual(result["corrected"]["grounding"], "talks-1")
        self.assertEqual(result["corrected"]["figure"], 0.2)

    def test_other_weights_get_no_corrected_figure(self):
        with tempfile.TemporaryDirectory() as d:
            panel = panel_with(d, ("smoke-1", {}))
            run_json("ground", os.path.join(panel, "real", "smoke-1.json"))
            result, code = run_json("aggregate", os.path.join(panel, "rounds", "r1"), "--weights", "1,0.5,0,0,0")
        self.assertEqual(code, 0, result)
        self.assertIsNone(result["corrected"]["figure"])
        self.assertIn("top-box 75/25/10/5/2", result["corrected"]["problem"])

    def test_a_damaged_grounding_ledger_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            panel = panel_with(d)
            write(d, "grounding.jsonl", '{"label": "smoke-1", "test": "smoke-test"}\n')
            result, code = run_json("aggregate", os.path.join(panel, "rounds", "r1"))
        self.assertEqual(code, 3)
        self.assertIn("ratio", [e["field"] for e in result["errors"]])


def grounded(d):
    """The normal panel at d/panel with r2 (second_round) and smoke-1 grounded on r1: ratio 0.35."""
    panel = panel_with(d, ("smoke-1", {}))
    run_json("ground", os.path.join(panel, "real", "smoke-1.json"))
    return panel, os.path.join(panel, "rounds", "r1"), second_round(panel)


class CorrectedInEveryReport(unittest.TestCase):
    """r1: discounted 1.10 / 7, corrected 0.35 x 1.10 / 7 = 0.055; r2: 2.25 / 7, corrected 0.1125."""

    def test_diff_shows_the_corrected_figure_before_and_after(self):
        with tempfile.TemporaryDirectory() as d:
            _, r1, r2 = grounded(d)
            result, code = run_json("diff", r1, r2)
            text = run("diff", r1, r2).stdout
        self.assertEqual(code, 0, result)
        c = result["corrected"]
        self.assertEqual((c["before"]["figure"], c["after"]["figure"]), (0.055, 0.1125))
        self.assertIn("Corrected: r1 5.5%, r2 11.2% conversions per visit", text)

    def test_competitor_shows_the_corrected_figure(self):
        with tempfile.TemporaryDirectory() as d:
            panel = panel_with(d, ("smoke-1", {}))
            shutil.copytree(os.path.join(FIXTURES, "competitor"), panel, dirs_exist_ok=True)
            run_json("ground", os.path.join(panel, "real", "smoke-1.json"))
            result, code = run_json("competitor", os.path.join(panel, "rounds", "r1"),
                                    os.path.join(panel, "rounds", "r2"))
        self.assertEqual(code, 0, result)
        self.assertEqual(result["corrected"]["before"]["figure"], 0.055)

    def test_objections_show_the_corrected_prediction(self):
        with tempfile.TemporaryDirectory() as d:
            _, r1, _ = grounded(d)
            result, code = run_json("objections", r1)
            text = run("objections", r1).stdout
        self.assertEqual(code, 0, result)
        self.assertEqual(result["predicted"]["corrected"]["figure"], 0.055)
        self.assertIn("Corrected: 5.5% conversions per visit", text)

    def test_the_page_shows_the_corrected_figure(self):
        with tempfile.TemporaryDirectory() as d:
            _, r1, _ = grounded(d)
            _, code = run_json("page", r1)
            with open(os.path.join(r1, "page.json"), encoding="utf-8") as f:
                data = json.load(f)
            with open(os.path.join(r1, "page.html"), encoding="utf-8") as f:
                html = f.read()
        self.assertEqual(code, 0)
        self.assertEqual(data["summary"]["corrected"]["figure"], 0.055)
        self.assertIn("<dt>Corrected</dt>", html)

    def test_quotes_show_the_corrected_first_round_of_the_held_out_buyers(self):
        with tempfile.TemporaryDirectory() as d:
            _, r1, _ = grounded(d)
            result, code = run_json("quotes", r1, "--seed", "1")
            text = run("quotes", r1, "--seed", "1").stdout
        self.assertEqual(code, 0, result)
        first = result["first_round"]
        self.assertAlmostEqual(first["corrected"]["figure"], 0.35 * first["discounted"], places=3)
        self.assertIn("Corrected:", text)

    def test_compare_shows_the_corrected_figure_on_each_side(self):
        with tempfile.TemporaryDirectory() as d:
            panel = panel_with(d, ("smoke-1", {}))
            shutil.copytree(os.path.join(FIXTURES, "compare"), panel, dirs_exist_ok=True)
            run_json("ground", os.path.join(panel, "real", "smoke-1.json"))
            a, b = os.path.join(panel, "rounds", "r2-A"), os.path.join(panel, "rounds", "r2-B")
            result, code = run_json("compare", a, b)
            text = run("compare", a, b).stdout
        self.assertEqual(code, 0, result)
        # A: 0.35 x 0.75 / 4 = 0.0656; B: 0.35 x 1.00 / 3 = 0.1167
        self.assertEqual((result["a"]["corrected"]["figure"], result["b"]["corrected"]["figure"]), (0.0656, 0.1167))
        self.assertIn("Corrected: r2-A 6.6%, r2-B 11.7% conversions per visit", text)

    def test_revenue_shows_the_corrected_figure_at_each_price(self):
        with tempfile.TemporaryDirectory() as d:
            panel = os.path.join(d, "price")
            shutil.copytree(os.path.join(FIXTURES, "price"), panel)
            real(panel, "smoke-1", round="p1-9")
            run_json("ground", os.path.join(panel, "real", "smoke-1.json"))
            rounds = [os.path.join(panel, "rounds", x) for x in ("p1-9", "p1-14", "p1-24")]
            result, code = run_json("revenue", *rounds)
            text = run("revenue", *rounds).stdout
        self.assertEqual(code, 0, result)
        # ratio 0.055 / (1.65 / 7) = 0.2333; times 1.65, 1.10 and 0.35 discounted buyers, over 7
        self.assertEqual([r["corrected"]["figure"] for r in result["rounds"]], [0.055, 0.0367, 0.0117])
        self.assertIn("Corrected: p1-9 5.5%, p1-14 3.7%, p1-24 1.2% conversions per visit", text)


if __name__ == "__main__":
    unittest.main()
