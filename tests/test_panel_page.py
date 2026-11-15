"""Tests for skills/buyer-panel/scripts/panel.py page. Run: python -m unittest discover -s tests"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

from test_panel import ROOT, copy_round, run_json

DESIGNSCAN = os.path.join(ROOT, "skills", "ai-slop-design", "scripts", "designscan.py")

SIMULATED = ("Simulated panel: 7 synthetic buyers written by test-model-1, not real people. "
             "Every number below is a hypothesis to test on people.")


def page(r1, *extra):
    result, code = run_json("page", r1, *extra)
    with open(os.path.join(r1, "page.json"), encoding="utf-8") as f:
        data = json.load(f)
    with open(os.path.join(r1, "page.html"), encoding="utf-8") as f:
        html = f.read()
    return result, code, data, html


class PageData(unittest.TestCase):
    def test_page_data_for_the_normal_round(self):
        with tempfile.TemporaryDirectory() as d:
            result, code, data, _ = page(copy_round(d))
        self.assertEqual(code, 0, result)
        self.assertEqual(data["simulated"], SIMULATED)
        self.assertEqual(data["idea"], "A time tracker that starts itself when you open a client's files.")
        self.assertEqual(data["round"]["label"], "r1")
        self.assertEqual([r["buyer_id"] for r in data["rows"]], ["b01", "b02", "b03", "b04", "b05", "b06", "b07"])
        self.assertEqual(data["filters"], {
            "segment": ["solo", "studio", "agency", "school"],
            "decision": ["BUY", "PASS"],
            "reason": ["already-paid", "better-quotes", "no-need", "saves-time"],
        })
        # 3 of 7 chose the offer; discounted (0.75 + 0.25 + 0.1) / 7 = 0.1571
        self.assertEqual((data["summary"]["buy_share"]["buy"], data["summary"]["buy_share"]["discounted"]),
                         (3, 0.1571))

    def test_price_chart_points_come_from_the_answers_in_order(self):
        # b05 and b07 answered out of order, so five answers draw the curves.
        with tempfile.TemporaryDirectory() as d:
            _, _, data, _ = page(copy_round(d))
        chart = data["chart"]
        self.assertEqual(chart["answers"], 5)
        points = {p["price"]: p for p in chart["points"]}
        self.assertEqual(sorted(points), [4, 5, 6, 7, 8, 9, 10, 11, 12, 15, 18, 20, 22, 25, 28, 30, 35, 40])
        # at 10: nobody calls it too cheap; cheap at 10 or more for b01, b02, b04, b06; nobody finds it expensive
        self.assertEqual({k: points[10][k] for k in ("too_cheap", "cheap", "expensive", "too_expensive")},
                         {"too_cheap": 0.0, "cheap": 0.8, "expensive": 0.0, "too_expensive": 0.0})
        # at 25: all five find it expensive, only b03 too expensive
        self.assertEqual({k: points[25][k] for k in ("too_cheap", "cheap", "expensive", "too_expensive")},
                         {"too_cheap": 0.0, "cheap": 0.0, "expensive": 1.0, "too_expensive": 0.2})


class PageHtml(unittest.TestCase):
    def test_simulated_line_comes_before_anything_else_on_the_page(self):
        with tempfile.TemporaryDirectory() as d:
            _, _, _, html = page(copy_round(d))
        body = html[html.index("<body"):]
        self.assertIn(SIMULATED, body)
        self.assertLess(body.index(SIMULATED), body.index("<h1"))

    def test_table_rows_carry_what_the_filters_select_on(self):
        with tempfile.TemporaryDirectory() as d:
            _, _, _, html = page(copy_round(d))
        self.assertEqual(html.count("<tr data-segment="), 7)
        self.assertIn('<tr data-segment="studio" data-decision="PASS" data-reason="already-paid">', html)
        for name in ("segment", "decision", "reason"):
            self.assertIn(f'<select id="filter-{name}"', html)
        self.assertIn('<option value="saves-time">saves-time</option>', html)

    def test_page_is_self_contained_with_an_inline_price_chart(self):
        with tempfile.TemporaryDirectory() as d:
            _, _, _, html = page(copy_round(d))
        self.assertIn("<svg", html)
        self.assertEqual(html.count("<polyline"), 4)
        for outside in ("<link", "src=", "@import", "url("):
            self.assertNotIn(outside, html)
        self.assertIn('<meta name="viewport"', html)
        self.assertIn("prefers-color-scheme: dark", html)

    def test_buyer_text_is_escaped(self):
        with tempfile.TemporaryDirectory() as d:
            r1 = copy_round(d)
            buyers = os.path.join(r1, os.pardir, os.pardir, "buyers.jsonl")
            with open(buyers, encoding="utf-8") as f:
                text = f.read()
            with open(buyers, "w", encoding="utf-8", newline="\n") as f:
                f.write(text.replace("Ana Ruiz", "Ana <script>Ruiz</script>"))
            _, code, _, html = page(r1)
        self.assertEqual(code, 0)
        self.assertNotIn("<script>Ruiz", html)
        self.assertIn("Ana &lt;script&gt;Ruiz&lt;/script&gt;", html)


class PageChecks(unittest.TestCase):
    def test_no_checks_section_without_checks(self):
        with tempfile.TemporaryDirectory() as d:
            _, code, data, html = page(copy_round(d))
        self.assertEqual(code, 0)
        self.assertIsNone(data["checks"])
        self.assertNotIn('id="checks"', html)

    def test_checks_from_the_round_summary_are_shown(self):
        checks = [{"name": "intent-spread", "passed": False, "value": 1.2, "threshold": 1.0},
                  {"name": "first-position", "passed": True}]
        with tempfile.TemporaryDirectory() as d:
            r1 = copy_round(d)
            with open(os.path.join(r1, "summary.json"), "w", encoding="utf-8") as f:
                json.dump({"checks": checks}, f)
            _, code, data, html = page(r1)
        self.assertEqual(code, 0)
        self.assertEqual(data["checks"], checks)
        self.assertIn('<strong>intent-spread</strong> <span class="failed">failed</span>: value 1.2, threshold 1.0',
                      html)
        self.assertIn('<strong>first-position</strong> <span class="passed">passed</span>', html)

    def test_an_unreadable_summary_is_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            r1 = copy_round(d)
            with open(os.path.join(r1, "summary.json"), "w", encoding="utf-8") as f:
                f.write("[not json")
            _, code, data, _ = page(r1)
        self.assertEqual((code, data["checks"]), (0, None))


class PageDesign(unittest.TestCase):
    """The page passes ai-slop-design's scanner with no open S or M hit, with and without its calibration."""

    def scan(self, no_calibration):
        env = dict(os.environ)
        env.pop("SUPAH_DESIGN_NO_CALIBRATION", None)
        if no_calibration:
            env["SUPAH_DESIGN_NO_CALIBRATION"] = "1"
        checks = [{"name": "intent-spread", "passed": False, "value": 1.2}]
        with tempfile.TemporaryDirectory() as d:
            r1 = copy_round(d)
            with open(os.path.join(r1, "summary.json"), "w", encoding="utf-8") as f:
                json.dump({"checks": checks}, f)
            page(r1)
            out = subprocess.run([sys.executable, DESIGNSCAN, "--json", os.path.join(r1, "page.html")],
                                 capture_output=True, text=True, encoding="utf-8", env=env, timeout=60)
        open_hits = [h for h in json.loads(out.stdout)[0]["hits"] if h["tier"] in ("S", "M")]
        self.assertEqual((out.returncode, open_hits), (0, []))

    def test_no_open_hit_with_calibration(self):
        self.scan(no_calibration=False)

    def test_no_open_hit_with_catalogue_tiers(self):
        self.scan(no_calibration=True)


if __name__ == "__main__":
    unittest.main()
