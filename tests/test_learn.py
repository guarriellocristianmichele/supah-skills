"""Tests for the verdict learning in skills/ai-slop-prose/scripts/learn.py."""
import math
import os
import random
import shutil
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

    def test_human_verdict_overrides_model(self):
        ctx = "we [delve] into"
        learn.record([verdict("fp", match="delve", context=ctx), verdict("fp", match="delve", context=ctx),
                      verdict("tell", match="delve", context=ctx, source="human")])
        model = learn.rebuild()
        self.assertEqual(model["suppress"], [])
        self.assertEqual(model["verdicts"], 1)


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


if __name__ == "__main__":
    unittest.main()
