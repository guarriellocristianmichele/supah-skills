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


def run(*args, cwd=None):
    env = dict(os.environ, PYTHONIOENCODING="utf-8", SUPAH_PROSE_HOME=ISOLATED,
               SUPAH_PROSE_NO_CALIBRATION="1")  # designed tiers; calibration is tested on its own  # never the user's learned model
    return subprocess.run([sys.executable, SCAN, *args], capture_output=True, text=True,
                          encoding="utf-8", env=env, cwd=cwd)


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
        for rule in ("chat-residue", "staged-opener", "not-x-its-y", "countdown", "self-question",
                     "inflated", "ing-tail", "importance-flag", "tradeoff-denial", "filler-transition",
                     "signposted-ending", "copula-avoidance", "marked-word", "bold-lead-bullet",
                     "title-case", "fragment-run", "em-dash", "vague-attribution"):
            self.assertIn(rule, rules(r), rule)

    def test_italian_slop(self):
        r, code = scan_json("slop-it.md")
        self.assertEqual(r["lang"], "it")
        self.assertEqual(code, 1)
        for rule in ("chat-residue", "not-x-its-y", "countdown", "self-question", "inflated",
                     "ing-tail", "importance-flag", "vague-attribution", "em-dash"):
            self.assertIn(rule, rules(r), rule)
        self.assertIn("summary-closer", rules(r, "W"))  # "In conclusione" is common in human Italian too

    def test_italian_assistant_residue(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "it.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write("Perfetto! Ecco una proposta per la tua email.\n\n**Oggetto della mail**\n\n"
                        "Se hai domande, non esitare a scrivermi: sono qui e posso aiutarti a sistemarla.\n\n"
                        "In sintesi, la mail è pronta da inviare al tuo responsabile.\n")
            out = json.loads(run("--json", "--lang", "it", path).stdout)[0]
        found = {h["rule"] for h in out["hits"]}
        for rule in ("chat-residue", "ecco-opener", "bold-heading", "signposted-ending"):
            self.assertIn(rule, found, rule)

    def test_english_sign_off_without_you(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "en.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write("The cache keeps the last ten results.\n\nLet me know if anything needs changing.\n"
                        "Just let me know whether the limit should be higher.\n")
            out = json.loads(run("--json", "--lang", "en", path).stdout)[0]
        matches = [h["match"] for h in out["hits"] if h["rule"] == "chat-residue"]
        self.assertEqual(len(matches), 2, matches)

    def test_split_contrast_with_contractions(self):
        r, _ = scan_json("contrast-en.md", "--lang", "en")
        lines = {h["line"] for h in r["hits"] if h["rule"] == "not-x-but-y"}
        self.assertEqual(lines, {1, 3, 5, 7}, r["hits"])

    def test_italian_hope_it_helps(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "it.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write("La procedura richiede due passaggi.\n\nSpero che questo ti sia utile!\n\n"
                        "Spero che questa guida vi sia d’aiuto.\n")
            out = json.loads(run("--json", "--lang", "it", path).stdout)[0]
        lines = {h["line"] for h in out["hits"] if h["rule"] == "chat-residue" and h["tier"] == "S"}
        self.assertEqual(lines, {3, 5}, out["hits"])

    def test_ecco_opener_reports_its_own_line(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "it.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write("La riunione è fissata per giovedì.\n\nEcco come preparare la sala.\n")
            out = json.loads(run("--json", "--lang", "it", path).stdout)[0]
        hit = next(h for h in out["hits"] if h["rule"] == "ecco-opener")
        self.assertEqual((hit["line"], hit["col"]), (3, 1))
        self.assertTrue(hit["match"].startswith("Ecco"), hit["match"])

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
                f.write("not-x-its-y\tisn't just a trend — it's\tquote\n")
                f.write("em-dash\t—\tquote\n")
            r, code = scan_json("compare-original.md", "--keep", keep)
            self.assertTrue(all(h["kept"] for h in r["hits"] if h["tier"] in "SM"))
            self.assertEqual(code, 0)

    def test_repository_keep_file_is_read_without_a_flag(self):
        # a hit kept on purpose stays kept next session: the keep file lives in the repository, not the scratchpad
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, ".git"), "w") as f:  # a worktree's .git is a file; found walking up
                f.write("gitdir: elsewhere\n")
            os.makedirs(os.path.join(d, "docs", "deep"))
            doc = os.path.join(d, "docs", "post.md")
            shutil.copy(os.path.join(FIX, "compare-original.md"), doc)
            with open(os.path.join(d, ".slop-prose-keep.tsv"), "w", encoding="utf-8-sig") as f:
                f.write("# kept on purpose\nnot-x-its-y\tisn't just a trend — it's\tquote\n")
            extra = os.path.join(d, "extra.tsv")
            with open(extra, "w", encoding="utf-8") as f:
                f.write("em-dash\t—\tquote\n")
            out = run("--json", "--keep", extra, doc, cwd=os.path.join(d, "docs", "deep"))
            r = json.loads(out.stdout)[0]
            self.assertEqual(out.returncode, 0, [h for h in r["hits"] if not h["kept"]])
            self.assertEqual(run(doc, cwd=d).returncode, 1)  # the em dashes are kept only by --keep
            missing = run("--keep", os.path.join(d, "nope.tsv"), doc, cwd=d)
        self.assertEqual(missing.returncode, 2)
        self.assertIn("keep file not found", missing.stderr)

    def test_outside_a_repository_the_keep_file_of_the_current_folder_is_read(self):
        with tempfile.TemporaryDirectory() as d:
            doc = os.path.join(d, "post.md")
            shutil.copy(os.path.join(FIX, "compare-original.md"), doc)
            with open(os.path.join(d, ".slop-prose-keep.tsv"), "w", encoding="utf-8") as f:
                f.write("not-x-its-y\tisn't just a trend — it's\tquote\nem-dash\t—\tquote\n")
            self.assertEqual(run(doc, cwd=d).returncode, 0)

    def test_an_empty_file_has_no_words(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "empty.md")
            open(path, "w").close()
            out = json.loads(run("--json", path).stdout)[0]
        self.assertEqual(out["metrics"]["words"], 0)


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

    def test_fixed_capitals_are_not_lost_names(self):
        # sentence-casing a Title Case heading or lowering a capital after a colon keeps the words
        out = run("compare", os.path.join(FIX, "compare-case-original.md"), os.path.join(FIX, "compare-case-rewrite.md"))
        self.assertEqual(out.returncode, 0, out.stdout)

    def test_a_rewritten_title_case_run_is_not_a_lost_name(self):
        with tempfile.TemporaryDirectory() as d:
            orig, final = os.path.join(d, "orig.md"), os.path.join(d, "final.md")
            with open(orig, "w", encoding="utf-8") as f:
                f.write("# Unlock The Power Of Your Data\n\nWe send every report to Acme Corp.\n")
            with open(final, "w", encoding="utf-8") as f:
                f.write("# Get more from your data\n\nWe send every report to Acme Corp.\n")
            out = run("compare", orig, final)
            self.assertEqual(out.returncode, 0, out.stdout)
            with open(final, "w", encoding="utf-8") as f:
                f.write("# Get more from your data\n\nWe send every report to the company.\n")
            out = run("compare", orig, final)
        self.assertEqual(out.returncode, 1)  # a name in a sentence is still a fact
        self.assertIn("Acme Corp", out.stdout)

    def test_identical_files_pass(self):
        path = os.path.join(FIX, "slop-en.md")
        self.assertEqual(run("compare", path, path).returncode, 0)


class SourceSweep(unittest.TestCase):
    """A sweep of a source file: the snapshot keeps the extension, so it is read as the same kind of file."""
    ORIGINAL = ('// We delve into the robust signup flow here.\n'
                'export function Signup() {\n'
                '  return <button title="Unlock the full potential of your team">Join 2,000 teams</button>;\n'
                '}\n')
    REWRITE = ORIGINAL.replace("Unlock the full potential of your team", "Start your free trial")

    def sweep(self, d, snapshot_name):
        orig, final = os.path.join(d, snapshot_name), os.path.join(d, "Signup.tsx")
        for path, text in ((orig, self.ORIGINAL), (final, self.REWRITE)):
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
        home = os.path.join(d, "home")
        env = dict(os.environ, PYTHONIOENCODING="utf-8", SUPAH_PROSE_HOME=home, SUPAH_PROSE_NO_CALIBRATION="1")
        compare = subprocess.run([sys.executable, SCAN, "compare", orig, final], capture_output=True,
                                 text=True, encoding="utf-8", env=env)
        verdict = subprocess.run([sys.executable, SCAN, "verdict", orig, final], capture_output=True,
                                 text=True, encoding="utf-8", env=env)
        log = read(os.path.join(home, "verdicts.tsv")) if os.path.exists(os.path.join(home, "verdicts.tsv")) else ""
        return compare, verdict, log

    def test_snapshot_named_stem_orig_ext_completes_the_sweep(self):
        with tempfile.TemporaryDirectory() as d:
            compare, verdict, log = self.sweep(d, "Signup.orig.tsx")
        self.assertEqual(compare.returncode, 0, compare.stdout)  # a rewritten UI string is not a lost quote
        self.assertEqual(verdict.returncode, 0, verdict.stderr)
        self.assertIn("inflated", log)  # the rewritten UI string is a tell
        self.assertNotIn("delve", log.lower())  # the code comment was never prose

    def test_compare_keeps_facts_of_ui_strings(self):
        with tempfile.TemporaryDirectory() as d:
            orig, final = os.path.join(d, "Signup.orig.tsx"), os.path.join(d, "Signup.tsx")
            with open(orig, "w", encoding="utf-8") as f:
                f.write(self.ORIGINAL)
            with open(final, "w", encoding="utf-8") as f:
                f.write(self.ORIGINAL.replace("Join 2,000 teams", "Join our teams"))
            out = run("compare", orig, final)
        self.assertEqual(out.returncode, 1)
        self.assertIn("2,000", out.stdout)


class Rules(unittest.TestCase):
    def test_every_category_matches_a_tells_heading(self):
        tells = read(os.path.join(ROOT, "skills", "ai-slop-prose", "TELLS.md"))
        out = run("rules").stdout
        cats = {line.split("|")[2].strip() for line in out.splitlines()
                if line.startswith("| ") and line.count("|") == 5 and "category" not in line}
        for cat in cats:
            self.assertRegex(tells, rf"## \d+\. {cat}\n", cat)

    def test_every_rule_is_listed_in_tells(self):
        tells = read(os.path.join(ROOT, "skills", "ai-slop-prose", "TELLS.md"))
        out = run("rules").stdout
        rules = {line.split("|")[1].strip() for line in out.splitlines()
                 if line.startswith("| ") and line.count("|") == 5 and "category" not in line}
        for rule in rules:
            self.assertIn(f"`{rule}`", tells, rule)


if __name__ == "__main__":
    unittest.main()
