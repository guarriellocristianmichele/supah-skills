"""Tests for the verdict learning in skills/ai-slop-prose/scripts/learn.py."""
import json
import math
import os
import random
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "skills", "ai-slop-prose", "scripts"))
import learn  # noqa: E402


def verdict(label, rule="marked-word", tier="M", match="pivotal", context=None, source="model", i=0):
    return {"lang": "en", "rule": rule, "category": "vocabulary", "tier": tier, "label": label,
            "reason": "test", "source": source, "match": match,
            "context": context or f"sentence number {i} with a [pivotal] word"}


class Isolated(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.old = os.environ.get("SUPAH_PROSE_HOME")
        os.environ["SUPAH_PROSE_HOME"] = self.dir

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)
        if self.old is None:
            os.environ.pop("SUPAH_PROSE_HOME", None)
        else:
            os.environ["SUPAH_PROSE_HOME"] = self.old


class BetaMath(unittest.TestCase):
    def test_closed_forms(self):
        for x in (0.1, 0.5, 0.9):
            self.assertAlmostEqual(learn.beta_cdf(x, 1, 1), x, places=9)
            self.assertAlmostEqual(learn.beta_cdf(x, 2, 1), x ** 2, places=9)
            self.assertAlmostEqual(learn.beta_cdf(x, 1, 3), 1 - (1 - x) ** 3, places=9)

    def test_quantile_inverts_cdf(self):
        q = learn.beta_quantile(0.05, 13.4, 4.2)
        self.assertAlmostEqual(learn.beta_cdf(q, 13.4, 4.2), 0.05, places=6)

    def test_monte_carlo_agrees(self):
        rng = random.Random(7)
        mc = sum(rng.betavariate(5.5, 2.5) < 0.6 for _ in range(100000)) / 100000
        self.assertLess(abs(learn.beta_cdf(0.6, 5.5, 2.5) - mc), 0.01)


class Demotion(Isolated):
    def test_no_tier_change_before_minimum_verdicts(self):
        learn.record([verdict("fp", i=i) for i in range(learn.MIN_VERDICTS - 1)])
        self.assertEqual(learn.rebuild()["rules"]["marked-word/en"]["tier"], "M")

    def test_noisy_rule_is_demoted(self):
        learn.record([verdict("fp", i=i) for i in range(40)])
        rule = learn.rebuild()["rules"]["marked-word/en"]
        self.assertIn(rule["tier"], ("W", "off"))
        self.assertLess(rule["lower95"], learn.TARGETS["M"])

    def test_mostly_right_rule_keeps_its_tier(self):
        learn.record([verdict("fp" if i % 5 == 0 else "tell", i=i) for i in range(60)])  # 80% precision
        self.assertEqual(learn.rebuild()["rules"]["marked-word/en"]["tier"], "M")

    def test_recent_verdicts_weigh_more(self):
        old = [verdict("fp", i=i) for i in range(60)]
        new = [verdict("tell", i=100 + i) for i in range(200)]
        learn.record(old + new)
        self.assertEqual(learn.rebuild()["rules"]["marked-word/en"]["tier"], "M")


class ContextSuppression(Isolated):
    def test_repeated_fp_in_same_context_is_suppressed(self):
        ctx = "the [Delve] library parses"
        learn.record([verdict("fp", match="Delve", context=ctx), verdict("fp", match="Delve", context=ctx)])
        model = learn.rebuild()
        hit = {"rule": "marked-word", "category": "vocabulary", "tier": "M", "match": "Delve",
               "context": ctx, "line": 3}
        self.assertEqual(learn.apply(model, hit, "en")[1], "learned:context")

    def test_a_single_tell_blocks_suppression(self):
        ctx = "the [Delve] library parses"
        learn.record([verdict(l, match="Delve", context=ctx) for l in ("fp", "fp", "tell")])
        self.assertEqual(learn.rebuild()["suppress"], [])

    def test_the_latest_human_verdict_on_a_context_is_the_one_that_counts(self):
        ctx = "we [delve] into"
        learn.record([verdict("fp", match="delve", context=ctx, source="human"),
                      verdict("tell", match="delve", context=ctx, source="human")])
        model = learn.rebuild()
        self.assertEqual(model["verdicts"], 1)
        self.assertEqual(model["rules"]["marked-word/en"]["counts"]["tell"], 1)

    def test_human_verdict_overrides_model(self):
        ctx = "we [delve] into"
        learn.record([verdict("fp", match="delve", context=ctx), verdict("fp", match="delve", context=ctx),
                      verdict("tell", match="delve", context=ctx, source="human")])
        model = learn.rebuild()
        self.assertEqual(model["suppress"], [])
        self.assertEqual(model["verdicts"], 1)

    def test_a_model_verdict_that_agrees_with_the_human_label_still_counts(self):
        ctx = "the [Delve] library parses"
        learn.record([verdict("fp", match="Delve", context=ctx, source="human"),
                      verdict("fp", match="Delve", context=ctx)])
        model = learn.rebuild()
        self.assertEqual(model["verdicts"], 2)
        hit = {"rule": "marked-word", "category": "vocabulary", "tier": "M", "match": "Delve",
               "context": ctx, "line": 3}
        self.assertEqual(learn.apply(model, hit, "en")[1], "learned:context")

    def test_a_later_model_verdict_that_disagrees_with_the_human_label_is_dropped(self):
        ctx = "the [Delve] library parses"
        learn.record([verdict("fp", match="Delve", context=ctx, source="human"),
                      verdict("tell", match="Delve", context=ctx)])
        model = learn.rebuild()
        self.assertEqual(model["verdicts"], 1)
        self.assertEqual(model["rules"]["marked-word/en"]["counts"]["fp"], 1)


class NaiveBayesGate(Isolated):
    def test_untrained_below_minimum(self):
        learn.record([verdict("fp", i=i) for i in range(50)])
        self.assertEqual(learn.rebuild()["nb"], {})

    def test_trained_suppressor_separates_contexts(self):
        rows = [verdict("fp", context=f"the [Delve] library function call {i}", i=i) for i in range(120)]
        rows += [verdict("tell", context=f"let us [delve] into the rich world {i}", i=i) for i in range(120)]
        learn.record(rows)
        model = learn.rebuild()
        self.assertIn("vocabulary/en", model["nb"])
        p_fp = learn.nb_fp_probability(model, "vocabulary", "en", "the [Delve] library function")
        p_tell = learn.nb_fp_probability(model, "vocabulary", "en", "let us [delve] into the rich world")
        self.assertGreater(p_fp, learn.NB_SUPPRESS)
        self.assertLess(p_tell, 0.5)


class Audit(Isolated):
    def test_samples_only_model_fp(self):
        learn.record([verdict("fp", i=i) for i in range(20)] + [verdict("tell", i=50 + i) for i in range(20)])
        sample = learn.audit_sample(0.1, seed=1)
        self.assertEqual(len(sample), math.ceil(20 * 0.1))
        self.assertTrue(all(r["label"] == "fp" for r in sample))

    def test_a_context_a_human_already_labelled_is_not_sampled_again(self):
        ctx = "the [Delve] library parses"
        learn.record([verdict("fp", match="Delve", context=ctx, source="human"),
                      verdict("fp", match="Delve", context=ctx)])
        self.assertEqual(learn.audit_sample(1.0, seed=1), [])


class Progress(Isolated):
    def test_a_rule_below_the_minimum_shows_how_far_it_is(self):
        learn.record([verdict("fp" if i % 4 == 0 else "tell", i=i) for i in range(12)])
        line = learn.progress(learn.rebuild(), ["marked-word/en"], "scan.py audit")[0]
        self.assertTrue(line.startswith("marked-word/en: 12/30 verdicts, precision so far 0."), line)
        self.assertTrue(line.endswith("tier M"), line)

    def test_a_tier_change_on_model_verdicts_alone_asks_for_an_audit(self):
        learn.record([verdict("fp", i=i) for i in range(20)])
        line = learn.progress(learn.rebuild(), ["marked-word/en"], "scan.py audit")[0]
        self.assertIn("run `scan.py audit --rule marked-word`", line)

    def test_a_few_model_verdicts_do_not_ask_for_an_audit_yet(self):
        learn.record([verdict("fp", i=i) for i in range(3)])
        line = learn.progress(learn.rebuild(), ["marked-word/en"], "scan.py audit")[0]
        self.assertNotIn("audit", line)

    def test_the_audit_it_asks_for_samples_that_rule(self):
        learn.record([verdict("fp", i=i) for i in range(20)])
        line = learn.progress(learn.rebuild(), ["marked-word/en"], "scan.py audit")[0]
        self.assertIn("run `scan.py audit --rule marked-word`", line)
        learn.record([verdict("fp", rule="other-rule", i=100 + i) for i in range(20)])
        self.assertEqual({r["rule"] for r in learn.audit_sample(1.0, rule="marked-word")}, {"marked-word"})

    def test_a_human_verdict_on_the_rule_settles_the_audit(self):
        learn.record([verdict("fp", i=i) for i in range(20)] + [verdict("fp", i=99, source="human")])
        line = learn.progress(learn.rebuild(), ["marked-word/en"], "scan.py audit")[0]
        self.assertNotIn("audit", line)

    def test_a_rule_without_verdicts_is_listed_as_such(self):
        self.assertEqual(learn.progress(learn.rebuild(), ["marked-word/en"], "scan.py audit"),
                         ["marked-word/en: 0/30 verdicts"])


class Export(Isolated):
    def test_the_export_carries_counts_per_rule_and_no_content(self):
        rows = [verdict("fp", match="hunter2", context=f"password hunter2 in client file {i}", i=i) for i in range(3)]
        rows += [verdict("tell", match="delve", context="private roadmap: we delve", i=9),
                 verdict("kept", match="delve", context="a quote", i=10)]
        learn.record(rows)
        data = learn.export(learn.rebuild())
        text = json.dumps(data)
        for secret in ("hunter2", "password", "roadmap", "quote", "delve"):
            self.assertNotIn(secret, text)
        self.assertEqual(data["store"], "prose")
        self.assertEqual(data["rules"], [{"rule": "marked-word", "lang": "en", "base": "M", "tier": "M", "verdicts": 5,
                                          "tell": 1, "kept": 1, "fp": 3, "human": 0,
                                          "precision": data["rules"][0]["precision"],
                                          "lower95": data["rules"][0]["lower95"]}])


class ExportCommand(Isolated):
    def test_scan_py_export_writes_the_file_it_shows(self):
        learn.record([verdict("fp", i=i) for i in range(3)])
        out = os.path.join(self.dir, "out.json")
        scan = os.path.join(ROOT, "skills", "ai-slop-prose", "scripts", "scan.py")
        run = subprocess.run([sys.executable, scan, "export", "--out", out], capture_output=True, text=True,
                             encoding="utf-8", env=dict(os.environ, SUPAH_PROSE_HOME=self.dir), timeout=60)
        self.assertEqual(run.returncode, 0, run.stderr)
        with open(out, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["rules"][0]["fp"], 3)
        self.assertIn('"rule": "marked-word"', run.stdout)


class Once(Isolated):
    SCAN = os.path.join(ROOT, "skills", "ai-slop-prose", "scripts", "scan.py")

    def run_scan(self, *args):
        return subprocess.run([sys.executable, self.SCAN, *args], capture_output=True, text=True, encoding="utf-8",
                              env=dict(os.environ, SUPAH_PROSE_HOME=self.dir), timeout=60)

    def test_a_sweep_recorded_twice_counts_once(self):
        orig = os.path.join(self.dir, "orig.md")
        final = os.path.join(self.dir, "final.md")
        with open(orig, "w", encoding="utf-8") as f:
            f.write("We delve into the rich tapestry of options.\n")
        with open(final, "w", encoding="utf-8") as f:
            f.write("We look at the options.\n")
        first = self.run_scan("verdict", orig, final)
        second = self.run_scan("verdict", orig, final)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertNotIn("Recorded 0 verdicts", first.stdout)
        self.assertIn("Recorded 0 verdicts", second.stdout)

    def repo_with_keep(self, line):
        repo = os.path.join(self.dir, "repo")
        os.makedirs(repo)
        with open(os.path.join(repo, ".git"), "w") as f:
            f.write("gitdir: elsewhere\n")
        with open(os.path.join(repo, ".slop-prose-keep.tsv"), "w", encoding="utf-8") as f:
            f.write(line)
        return repo

    def test_a_keep_entry_seen_by_two_sweeps_is_one_judgment(self):
        # ADR 0018: each judgment once. The repository keep file is read on every sweep, so its entry
        # must not pile up verdicts (and two fp verdicts in one context would suppress it).
        repo = self.repo_with_keep("marked-word\tdelve\tfp\n")
        orig = os.path.join(self.dir, "doc.orig.md")
        final = os.path.join(repo, "doc.md")
        with open(orig, "w", encoding="utf-8") as f:
            f.write("We delve into the rich tapestry of options.\n")
        for text in ("We delve into the options.\n", "We delve into the set of options.\n"):
            with open(final, "w", encoding="utf-8") as f:
                f.write(text)
            out = self.run_scan("verdict", orig, final)
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertNotIn("Recorded 0 verdicts", out.stdout)
        model = learn.rebuild()
        rule = model["rules"]["marked-word/en"]
        self.assertEqual(rule["counts"]["fp"], 1, rule)
        self.assertEqual(rule["tier"], rule["base"])
        self.assertEqual(model["suppress"], [])

    def test_a_rewritten_hit_is_a_tell_even_when_a_keep_line_matches_it(self):
        repo = self.repo_with_keep("marked-word\tdelve\tfp\n")
        orig = os.path.join(self.dir, "doc.orig.md")
        final = os.path.join(repo, "doc.md")
        with open(orig, "w", encoding="utf-8") as f:
            f.write("We delve into the options.\n")
        with open(final, "w", encoding="utf-8") as f:
            f.write("We look at the options.\n")
        out = self.run_scan("verdict", orig, final)
        self.assertIn("fp 0", out.stdout)
        rows = [r for r in learn.read_log() if r["match"] == "delve"]
        self.assertEqual([r["label"] for r in rows], ["tell"])

    def test_an_audit_file_labelled_twice_counts_once(self):
        path = os.path.join(self.dir, "audit.tsv")
        with open(path, "w", encoding="utf-8") as f:
            f.write("label\tlang\trule\tcategory\ttier\tmatch\tcontext\n"
                    "fp\ten\tmarked-word\tvocabulary\tM\tdelve\tthe delve library\n")
        self.run_scan("label", path)
        self.assertIn("Recorded 0 human verdicts", self.run_scan("label", path).stdout)

    def test_export_without_out_writes_next_to_the_model_not_in_the_project(self):
        learn.record([verdict("fp", i=i) for i in range(2)])
        cwd = tempfile.mkdtemp()
        try:
            run = subprocess.run([sys.executable, self.SCAN, "export"], capture_output=True, text=True,
                                 encoding="utf-8", env=dict(os.environ, SUPAH_PROSE_HOME=self.dir), cwd=cwd, timeout=60)
            self.assertEqual(os.listdir(cwd), [])
            self.assertTrue(os.path.exists(os.path.join(self.dir, "supah-prose-learning.json")), run.stdout)
        finally:
            shutil.rmtree(cwd, ignore_errors=True)


class Stores(unittest.TestCase):
    """One learn.py serves the prose, design and code scanners, each with its own store."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.environ["SUPAH_DESIGN_HOME"] = self.dir

    def tearDown(self):
        learn.configure("prose")
        os.environ.pop("SUPAH_DESIGN_HOME", None)
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_each_scanner_keeps_its_own_store(self):
        learn.configure("design")
        self.assertEqual(learn.paths(), (os.path.join(self.dir, "verdicts.tsv"), os.path.join(self.dir, "model.json")))

    def test_a_log_with_its_own_columns_and_no_language_is_learned_from(self):
        learn.configure("design")
        with open(os.path.join(self.dir, "verdicts.tsv"), "w", encoding="utf-8") as f:
            f.write("time\trule\tcategory\ttier\tlabel\treason\tsource\tfile\tmatch\tcontext\n")
            for i in range(40):
                f.write(f"2026-11-16T12:00:00\tpurple-gradient\tcolour\tM\tfp\tfp\tmodel\tapp.css\tviolet\tline {i}\n")
        rule = learn.rebuild()["rules"]["purple-gradient/-"]
        self.assertEqual((rule["n"], rule["base"]), (40, "M"))
        self.assertIn(rule["tier"], ("W", "off"))
        learn.record([{"rule": "purple-gradient", "category": "colour", "tier": "M", "label": "reflex",
                       "reason": "", "source": "model", "file": "b.css", "match": "violet", "context": "x"}])
        with open(os.path.join(self.dir, "verdicts.tsv"), encoding="utf-8") as f:
            self.assertTrue(f.read().splitlines()[-1].split("\t")[7] == "b.css")


if __name__ == "__main__":
    unittest.main()
