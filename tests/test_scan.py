"""Regression tests for skills/ai-slop-prose/scripts/scan.py. Run: python -m unittest discover -s tests"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN = os.path.join(ROOT, "skills", "ai-slop-prose", "scripts", "scan.py")
FIX = os.path.join(ROOT, "tests", "fixtures")
ISOLATED = tempfile.mkdtemp(prefix="supah-prose-test-")


def run(*args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8", SUPAH_PROSE_HOME=ISOLATED)  # never the user's learned model
    return subprocess.run([sys.executable, SCAN, *args], capture_output=True, text=True,
                          encoding="utf-8", env=env)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def scan_json(name, *extra):
    out = run("--json", *extra, os.path.join(FIX, name))
    return json.loads(out.stdout)[0], out.returncode


def rules(result, tiers="SM"):
    return {h["rule"] for h in result["hits"] if h["tier"] in tiers}


class ScanDetects(unittest.TestCase):
    def test_english_slop(self):
        r, code = scan_json("slop-en.md")
        self.assertEqual(r["lang"], "en")
        self.assertEqual(code, 1)
        for rule in ("chat-residue", "staged-opener", "not-x-but-y", "countdown", "self-question",
                     "inflated", "ing-tail", "importance-flag", "tradeoff-denial", "filler-transition",
                     "signposted-ending", "copula-avoidance", "marked-word", "bold-lead-bullet",
                     "title-case", "fragment-run", "em-dash"):
            self.assertIn(rule, rules(r), rule)

    def test_italian_slop(self):
        r, code = scan_json("slop-it.md")
        self.assertEqual(r["lang"], "it")
        self.assertEqual(code, 1)
        for rule in ("chat-residue", "not-x-but-y", "countdown", "self-question", "inflated",
                     "ing-tail", "importance-flag", "vague-attribution", "signposted-ending", "em-dash"):
            self.assertIn(rule, rules(r), rule)

    def test_italian_punctuation(self):
        r, _ = scan_json("punct-it.md")
        for rule in ("accent-error", "double-space", "space-before-punct", "space-after-comma",
                     "space-after-period", "exclamation-stack", "em-dash", "hyphen-as-dash"):
            self.assertIn(rule, rules(r), rule)
        self.assertIn("quote-mix", rules(r, "W"))


class ScanStaysQuiet(unittest.TestCase):
    def test_human_text_has_no_open_hits(self):
        r, code = scan_json("human-en.txt")
        self.assertEqual(rules(r), set())
        self.assertEqual(code, 0)

    def test_code_spans_are_ignored(self):
        r, _ = scan_json("punct-it.md")
        self.assertFalse(any("codice" in h["match"] for h in r["hits"]))


class KeepFile(unittest.TestCase):
    def test_kept_hits_and_metrics_resolve(self):
        with tempfile.TemporaryDirectory() as d:
            keep = os.path.join(d, "keep.tsv")
            with open(keep, "w", encoding="utf-8") as f:
                f.write("not-x-but-y\tisn't just a trend — it's\tquote\n")
                f.write("em-dash\t—\tquote\n")
            r, code = scan_json("compare-original.md", "--keep", keep)
            self.assertTrue(all(h["kept"] for h in r["hits"] if h["tier"] in "SM"))
            self.assertEqual(code, 0)


class Fix(unittest.TestCase):
    def test_fix_corrects_and_preserves_code(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "p.md")
            shutil.copy(os.path.join(FIX, "punct-it.md"), path)
            self.assertEqual(run("fix", path).returncode, 0)
            text = read(path)
            for good in ("È una scelta difficile, perché", "cambia. Qual è", "Un po' di",
                         "bene, anche da remoto", "Non so né", "`E' codice , non toccare`"):
                self.assertIn(good, text)
            r = json.loads(run("--json", path).stdout)[0]
            self.assertFalse(rules(r) & {"accent-error", "double-space", "space-before-punct",
                                         "space-after-comma", "space-after-period"})


    def test_fix_keeps_crlf_line_endings(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "crlf.md")
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write("Una riga , perchè.\r\nSeconda riga.\r\n")
            run("fix", path)
            with open(path, encoding="utf-8", newline="") as f:
                text = f.read()
            self.assertEqual(text, "Una riga, perché.\r\nSeconda riga.\r\n")


class Compare(unittest.TestCase):
    def test_reports_lost_facts(self):
        out = run("compare", os.path.join(FIX, "compare-original.md"), os.path.join(FIX, "compare-rewrite.md"))
        self.assertEqual(out.returncode, 1)
        for token in ("https://example.org/s", "`deploy.sh`", "Acme Corp"):
            self.assertIn(token, out.stdout)
        self.assertNotIn("| number | 38", out.stdout)

    def test_identical_files_pass(self):
        path = os.path.join(FIX, "slop-en.md")
        self.assertEqual(run("compare", path, path).returncode, 0)


class Rules(unittest.TestCase):
    def test_every_category_matches_a_tells_heading(self):
        tells = read(os.path.join(ROOT, "skills", "ai-slop-prose", "TELLS.md"))
        out = run("rules").stdout
        cats = {line.split("|")[2].strip() for line in out.splitlines()
                if line.startswith("| ") and line.count("|") == 5 and "category" not in line}
        for cat in cats:
            self.assertRegex(tells, rf"## \d+\. {cat}\n", cat)


if __name__ == "__main__":
    unittest.main()
