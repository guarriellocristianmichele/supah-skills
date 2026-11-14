"""Tests for skills/ai-slop-audit/scripts/codescan.py. Run: python -m unittest discover -s tests"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN = os.path.join(ROOT, "skills", "ai-slop-audit", "scripts", "codescan.py")
FIX = os.path.join(ROOT, "tests", "fixtures", "code")


def run(*args):
    env = dict(os.environ, SUPAH_CODE_NO_CALIBRATION="1")  # designed tiers; calibration is tested on its own
    return subprocess.run([sys.executable, SCAN, *args], capture_output=True, text=True, encoding="utf-8",
                          env=env, timeout=60)


def scan(path, *extra):
    out = run("--json", *extra, path)
    return json.loads(out.stdout)[0], out.returncode


def rules(result, tiers="SM"):
    return {h["rule"] for h in result["hits"] if h["tier"] in tiers}


class Python(unittest.TestCase):
    def test_slop(self):
        r, code = scan(os.path.join(FIX, "slop.py"))
        self.assertEqual(code, 1)
        self.assertEqual(rules(r), {"placeholder", "changelog-comment", "step-comment", "restating-comment",
                                    "restating-docstring", "emoji-output", "catch-rethrow", "swallowed-exception",
                                    "annotated-isinstance", "forwarding-wrapper"})
        self.assertEqual(rules(r, "W"), {"bool-return"})
        self.assertEqual(sum(h["rule"] == "restating-comment" for h in r["hits"]), 3)

    def test_human_code_is_clean(self):
        r, code = scan(os.path.join(FIX, "human.py"))
        self.assertEqual((code, r["hits"]), (0, []))

    def test_unparsable_syntax_is_skipped_not_guessed(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "bad.py")
            with open(path, "w", encoding="utf-8") as f:
                f.write("def f(:\n    pass\n")
            r, code = scan(path)
        self.assertIn("cannot parse", r["skipped"])
        self.assertEqual(code, 0)

    def test_keep_file_resolves_a_hit(self):
        with tempfile.TemporaryDirectory() as d:
            keep = os.path.join(d, "keep.tsv")
            with open(keep, "w", encoding="utf-8") as f:
                f.write("forwarding-wrapper\tdef read_config\tterm\n")
            r, _ = scan(os.path.join(FIX, "slop.py"), "--keep", keep)
        kept = [h for h in r["hits"] if h["rule"] == "forwarding-wrapper"]
        self.assertEqual(kept[0]["kept"], "term")


class JavaScript(unittest.TestCase):
    def test_slop(self):
        r, code = scan(os.path.join(FIX, "slop.ts"))
        self.assertEqual(code, 1)
        self.assertEqual(rules(r), {"placeholder", "changelog-comment", "step-comment", "restating-comment",
                                    "emoji-output", "catch-rethrow", "swallowed-exception", "forwarding-wrapper"})

    def test_forwarding_needs_identical_arguments(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "ok.js")
            with open(path, "w", encoding="utf-8") as f:
                f.write("function area(w, h) { return mul(w, h * 2); }\n"
                        "function pick(a, b = 1) { return choose(a, b); }\n")
            r, code = scan(path)
        self.assertEqual((code, r["hits"]), (0, []))


class Calibration(unittest.TestCase):
    def test_every_rule_has_a_calibrated_tier(self):
        sys.path.insert(0, os.path.dirname(SCAN))
        import codescan
        with open(codescan.CALIBRATION_FILE, encoding="utf-8") as f:
            rules = json.load(f)["rules"]
        for rule, (_, _, langs) in codescan.RULES.items():
            for lang in langs.split():
                with self.subTest(rule=rule, lang=lang):
                    self.assertIn(rules["%s/%s" % (rule, lang)]["tier"], ("S", "M", "W"))

    def test_shipped_tiers_follow_judged_precision(self):
        out = subprocess.run([sys.executable, SCAN, "rules"], capture_output=True, text=True, encoding="utf-8")
        tiers = {line.split("|")[1].strip(): line.split("|")[3].strip() for line in out.stdout.splitlines()[2:]}
        self.assertEqual(tiers["catch-rethrow"], "S/S")
        self.assertEqual(tiers["forwarding-wrapper"], "W/W")  # 5 of 8 judged hits were real


class Rules(unittest.TestCase):
    def test_lists_every_rule(self):
        out = run("rules")
        self.assertEqual(out.returncode, 0)
        for rule in ("placeholder", "forwarding-wrapper", "bool-return"):
            self.assertIn(rule, out.stdout)


if __name__ == "__main__":
    unittest.main()
