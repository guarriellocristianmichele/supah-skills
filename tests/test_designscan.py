"""Tests for skills/ai-slop-design/scripts/designscan.py. Run: python -m unittest discover -s tests"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN = os.path.join(ROOT, "skills", "ai-slop-design", "scripts", "designscan.py")
FIX = os.path.join(ROOT, "tests", "fixtures", "design")


def run(*args, env=None):
    base = dict(os.environ, SUPAH_DESIGN_NO_CALIBRATION="1")  # designed tiers; calibration is tested on its own
    base.pop("SUPAH_DESIGN_CALIBRATION", None)
    base.update(env or {})
    return subprocess.run([sys.executable, SCAN, *args], capture_output=True, text=True, encoding="utf-8",
                          env=base, timeout=60)


def scan(path, *extra, env=None):
    out = run("--json", *extra, path, env=env)
    return json.loads(out.stdout)[0], out.returncode


def write(d, name, text):
    path = os.path.join(d, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def rules(result, tiers="SM"):
    return {h["rule"] for h in result["hits"] if h["tier"] in tiers}


class Basics(unittest.TestCase):
    def test_gradient_text_is_an_open_hit(self):
        with tempfile.TemporaryDirectory() as d:
            path = write(d, "Hero.tsx", '<h1 className="bg-gradient-to-r from-pink-500 to-orange-400 '
                                        'bg-clip-text text-transparent">Hello</h1>\n')
            r, code = scan(path)
        self.assertEqual(code, 1)
        hit = [h for h in r["hits"] if h["rule"] == "gradient-text"][0]
        self.assertEqual((hit["line"], hit["category"], hit["tier"]), (1, "surface", "M"))
        self.assertIn("bg-clip-text", hit["context"])

    def test_keep_file_resolves_a_hit(self):
        with tempfile.TemporaryDirectory() as d:
            path = write(d, "a.css", ".title { -webkit-background-clip: text; }\n")
            keep = write(d, "keep.tsv", "gradient-text\t-webkit-background-clip: text\tbrand\n")
            r, code = scan(path, "--keep", keep)
        self.assertEqual((code, r["hits"][0]["kept"]), (0, "brand"))

    def test_non_frontend_file_is_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            r, code = scan(write(d, "notes.py", "x = 'bg-clip-text text-transparent'\n"))
        self.assertEqual((code, r["skipped"]), (0, "not a frontend source file"))


def found(name, category):
    r, _ = scan(os.path.join(FIX, name))
    return {h["rule"] for h in r["hits"] if h["category"] == category}


class Catalogue(unittest.TestCase):
    def test_colour(self):
        self.assertEqual(found("slop.tsx", "colour"), {"purple-gradient", "stock-swatch", "low-contrast"})
        self.assertEqual(found("slop.css", "colour"), {"purple-gradient", "cream-clay", "pure-black-white",
                                                       "near-black", "low-contrast"})
        self.assertEqual(found("slop.vue", "colour"), {"purple-gradient"})

    def test_contrast_threshold_depends_on_text_size(self):
        with tempfile.TemporaryDirectory() as d:
            r, _ = scan(write(d, "a.tsx", '<h2 className="text-3xl font-bold text-gray-500 bg-slate-900">Big</h2>\n'
                                          '<p className="text-white bg-slate-900">Fine</p>\n'
                                          '<p className="text-white/40 bg-slate-900">Faded</p>\n'))
        self.assertEqual([(h["line"], h["rule"]) for h in r["hits"]], [(3, "low-contrast")])
        self.assertIn(":1", r["hits"][0]["match"])

    def test_type(self):
        self.assertEqual(found("slop.tsx", "type"), {"eyebrow", "accent-word-heading", "tracked-caps", "mono-label"})
        self.assertEqual(found("slop.html", "type"), {"reflex-font"})

    def test_surface(self):
        self.assertEqual(found("slop.tsx", "surface"), {"gradient-text", "glass-card", "coloured-glow", "accent-stripe",
                                                        "shadcn-card"})
        self.assertEqual(found("slop.css", "surface"), {"glass-card", "coloured-glow", "accent-stripe"})
        self.assertEqual(found("slop.html", "surface"), {"uniform-radius", "soft-shadow"})

    def test_layout(self):
        self.assertEqual(found("slop.tsx", "layout"), {"icon-card-grid", "numbered-markers", "stat-banner", "vh-hero",
                                                       "faux-chrome"})
        self.assertEqual(found("slop.html", "layout"), {"faux-chrome"})
        self.assertEqual(found("slop.css", "layout"), {"vh-hero"})

    def test_glyph(self):
        self.assertEqual(found("slop.tsx", "glyph"), {"emoji-icon", "middot-meta", "glued-arrow", "word-dash-label",
                                                      "pulsing-dot"})
        self.assertEqual(found("slop.html", "glyph"), {"emoji-icon"})
        self.assertEqual(found("slop.vue", "glyph"), {"emoji-icon", "glued-arrow"})

    def test_motion(self):
        self.assertEqual(found("slop.tsx", "motion"), {"transition-all", "reveal-every-section", "hover-scale",
                                                       "no-reduced-motion"})
        self.assertEqual(found("slop.html", "motion"), {"transition-all"})
        self.assertEqual(found("slop.css", "motion"), {"bounce-easing", "no-reduced-motion"})
        self.assertEqual(found("slop.vue", "motion"), {"transition-all"})

    def test_placeholder(self):
        self.assertEqual(found("slop.tsx", "placeholder"), {"placeholder-name", "placeholder-phone", "dead-link"})
        self.assertEqual(found("slop.html", "placeholder"), {"placeholder-name"})
        self.assertEqual(found("slop.vue", "placeholder"), {"dead-link"})

    def test_responsive(self):
        self.assertEqual(found("slop.tsx", "responsive"), {"fixed-width", "unprefixed-grid", "hover-only",
                                                           "tiny-text", "viewport-width"})
        self.assertEqual(found("slop.css", "responsive"), {"fixed-width", "tiny-text"})
        self.assertEqual(found("slop.html", "responsive"), {"missing-viewport"})

    def test_capped_or_responsive_widths_are_fine(self):
        with tempfile.TemporaryDirectory() as d:
            r, _ = scan(write(d, "a.tsx", '<div className="w-[1200px] max-w-full">A</div>\n'
                                          '<div className="grid grid-cols-1 md:grid-cols-3">B</div>\n'
                                          '<span className="opacity-0 group-hover:opacity-100 group-focus-within:opacity-100">C</span>\n'))
        self.assertEqual(r["hits"], [])

    def test_duplication_counts_across_the_files_of_one_run(self):
        a, b, css = (os.path.join(FIX, n) for n in ("dup-a.tsx", "dup-b.tsx", "dup.css"))
        alone, _ = scan(a)
        self.assertEqual({h["category"] for h in alone["hits"]} & {"duplication"}, set())
        results = json.loads(run("--json", a, b, css).stdout)
        got = {(os.path.basename(r["file"]), h["rule"], h["line"]) for r in results for h in r["hits"]
               if h["category"] == "duplication"}
        self.assertEqual(got, {("dup-a.tsx", "repeated-class-string", 2), ("dup-b.tsx", "repeated-class-string", 2),
                               ("dup.css", "duplicate-css-block", 1), ("dup.css", "untokened-colour", 1)})

    def test_package_scope_is_not_a_placeholder(self):
        with tempfile.TemporaryDirectory() as d:
            r, _ = scan(write(d, "a.tsx", 'import { Button } from "@acme/ui";\n'))
        self.assertEqual(r["hits"], [])

    def test_grey_shadow_is_not_a_glow(self):
        with tempfile.TemporaryDirectory() as d:
            r, _ = scan(write(d, "a.css", ".a { box-shadow: 0 0 12px rgba(0, 0, 0, 0.3); }\n"))
        self.assertEqual(r["hits"], [])

    def test_reflex_font_reads_only_the_primary_face(self):
        with tempfile.TemporaryDirectory() as d:
            r, _ = scan(write(d, "a.css", 'body { font-family: "Alegreya Sans", Roboto, sans-serif; }\n'
                                          'h1 { font-family: Fraunces, serif; }\n'))
        self.assertEqual([(h["line"], h["rule"]) for h in r["hits"]], [(2, "reflex-font")])


class Clean(unittest.TestCase):
    def test_human_pages_have_no_hits(self):
        for name in ("human.html", "human.css", "human.tsx", "human.vue"):
            r, code = scan(os.path.join(FIX, name))
            self.assertEqual((name, code, r["hits"]), (name, 0, []))

    def test_chosen_uses_raise_no_open_hit(self):
        for name in ("chosen.tsx", "chosen.css"):
            r, code = scan(os.path.join(FIX, name))
            self.assertEqual((name, code, rules(r)), (name, 0, set()))

    def test_svelte_class_directives_are_read(self):
        self.assertEqual(found("slop.svelte", "colour"), {"purple-gradient"})


class Regressions(unittest.TestCase):
    """Cases a review reproduced against the first version of the scanner."""

    def hits(self, name, text):
        with tempfile.TemporaryDirectory() as d:
            r, _ = scan(write(d, name, text))
        return [(h["rule"], h["match"]) for h in r["hits"]]

    def test_quoted_value_inside_a_plain_class_keeps_the_whole_string(self):
        got = self.hits("a.html", """<h1 class="bg-[url('/h.jpg')] bg-gradient-to-r from-purple-500 to-blue-500 bg-clip-text text-transparent">Hi</h1>\n""")
        self.assertEqual({r for r, _ in got}, {"purple-gradient", "gradient-text"})

    def test_two_matches_of_one_rule_on_one_line_are_both_reported(self):
        got = self.hits("a.html", "<li>🚀 Fast</li><li>🔥 Hot</li>\n")
        self.assertEqual([m for r, m in got if r == "emoji-icon"], ["🚀 Fast", "🔥 Hot"])

    def test_large_text_does_not_depend_on_class_order(self):
        self.assertEqual(self.hits("a.tsx", '<p className="font-bold text-xl text-gray-500 bg-gray-100">x</p>\n'), [])
        self.assertEqual([r for r, _ in self.hits("a.tsx", '<p className="text-gray-500 bg-gray-100">x</p>\n')],
                         ["low-contrast"])

    def test_chromatic_hex_is_not_black_or_white(self):
        self.assertEqual(self.hits("a.css", ".a { color: #000fff; border-color: #fff000; }\n"), [])

    def test_small_viewport_units_are_the_fix_not_the_reflex(self):
        self.assertEqual(self.hits("a.tsx", '<section className="hero min-h-[80svh] max-h-[52rem]">x</section>\n'), [])

    def test_hamburger_and_check_glyphs_are_not_emoji(self):
        self.assertEqual(self.hits("a.html", "<button>☰</button><li>✓ Included</li>\n"), [])

    def test_tailwind_config_font_family_is_read(self):
        got = self.hits("tailwind.config.ts", 'theme: { extend: { fontFamily: { sans: ["Inter", "sans-serif"] } } }\n')
        self.assertEqual([r for r, _ in got], ["reflex-font"])

    def test_group_hover_scale_counts_as_hover_scale(self):
        cards = "".join('<div className="group-hover:scale-105">%d</div>\n' % i for i in range(3))
        self.assertIn("hover-scale", {r for r, _ in self.hits("a.tsx", cards)})

    def test_contrast_ignores_rules_that_colour_icons_and_rules_not_text(self):
        got = self.hits("a.css", ".social-link-x { color: #fafafa; background: #3288d4; }\n"
                                 ".w-bt1:hover hr { color: #ce3939; background-color: #ce3939; }\n"
                                 ".nav svg { color: #fafafa; background: #ff6c36; }\n"
                                 ".btn { color: #fafafa; background: #ff6c36; }\n")
        self.assertEqual([r for r, _ in got], ["low-contrast"])

    def test_arrows_drawing_a_flow_are_not_glued_to_a_label(self):
        self.assertEqual(self.hits("a.html", '<div class="flow-arrow">→ observation →</div>\n'), [])
        self.assertEqual([r for r, _ in self.hits("a.html", '<a href="/docs">Read the guide →</a>\n')], ["glued-arrow"])

    def test_custom_property_named_border_left_is_not_a_stripe(self):
        self.assertEqual(self.hits("a.css", ":root { --ifm-blockquote-border-left-width: 2px; border-radius: 4px; }\n"), [])

    def test_malformed_cubic_bezier_does_not_crash(self):
        self.assertEqual(self.hits("a.css", ".a { transition: transform 1s cubic-bezier(0, ., 1, 1); }\n"), [])

    def test_duplication_match_survives_a_partial_fix(self):
        six = "".join(".c%d { color: #2f6b4f; }\n" % i for i in range(6))
        five = "".join(".c%d { color: #2f6b4f; }\n" % i for i in range(5))
        colour = lambda text: [m for r, m in self.hits("a.css", text) if r == "untokened-colour"]  # noqa: E731
        self.assertEqual(colour(six), colour(five))

    def test_verdict_takes_every_pair_so_duplication_is_judged_across_files(self):
        with tempfile.TemporaryDirectory() as d:
            pairs = []
            for name in ("dup-a.tsx", "dup-b.tsx"):
                with open(os.path.join(FIX, name), encoding="utf-8") as f:
                    pairs += [write(d, name + ".orig", f.read()), write(d, name, "export {};\n")]
            out = run("verdict", *pairs, env={"SUPAH_DESIGN_HOME": d})
            with open(os.path.join(d, "verdicts.tsv"), encoding="utf-8") as f:
                rows = [line.split("\t") for line in f][1:]
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(sorted((r[1], r[4]) for r in rows), [("repeated-class-string", "reflex")] * 2)


class Docs(unittest.TestCase):
    def test_readme_states_the_rule_count(self):
        n = len(run("rules").stdout.splitlines()) - 2
        with open(os.path.join(ROOT, "skills", "ai-slop-design", "README.md"), encoding="utf-8") as f:
            self.assertIn("%d rules in" % n, f.read())


class Verdicts(unittest.TestCase):
    def test_every_resolved_hit_becomes_a_verdict(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(FIX, "slop.vue"), encoding="utf-8") as f:
                orig = write(d, "orig.vue", f.read())
            fixed = write(d, "page.vue", '<template>\n  <section>\n'
                                         '    <button :class="[\'bg-gradient-to-r from-violet-600 to-indigo-600\']">'
                                         'Start free trial →</button>\n'
                                         '    <p class="eyebrow">🔥 New</p>\n    <a href="#">Learn more</a>\n'
                                         '  </section>\n</template>\n')
            keep = write(d, "keep.tsv", "purple-gradient\tbg-gradient-to-r from-violet-600 to-indigo-600\tbrand\n"
                                        "emoji-icon\t🔥 New\tfp\n"
                                        "glued-arrow\tStart free trial →\thandoff\n")
            out = run("verdict", orig, fixed, "--keep", keep, env={"SUPAH_DESIGN_HOME": d})
            with open(os.path.join(d, "verdicts.tsv"), encoding="utf-8") as f:
                rows = [line.rstrip("\n").split("\t") for line in f][1:]
        self.assertEqual(out.returncode, 0, out.stderr)
        got = sorted((r[1], r[4], r[5]) for r in rows)
        self.assertEqual(got, [("emoji-icon", "fp", "fp"), ("glued-arrow", "reflex", "handoff"),
                               ("purple-gradient", "chosen", "brand"), ("transition-all", "reflex", "")])
        self.assertIn("1 unresolved", out.stdout)


class Calibration(unittest.TestCase):
    def test_calibrated_tier_overrides_the_designed_one(self):
        with tempfile.TemporaryDirectory() as d:
            path = write(d, "a.css", ".t { background-clip: text; }\n")
            cal = write(d, "cal.json", json.dumps({"rules": {"gradient-text": {"tier": "W"}}}))
            r, code = scan(path, env={"SUPAH_DESIGN_NO_CALIBRATION": "", "SUPAH_DESIGN_CALIBRATION": cal})
        self.assertEqual((code, r["hits"][0]["tier"]), (0, "W"))

    def test_every_rule_has_a_calibrated_entry(self):
        with open(os.path.join(ROOT, "skills", "ai-slop-design", "scripts", "designscan-calibration.json"),
                  encoding="utf-8") as f:
            calibrated = set(json.load(f)["rules"])
        listed = {line.split("|")[1].strip() for line in run("rules").stdout.splitlines()[2:]}
        self.assertEqual(listed, calibrated)


if __name__ == "__main__":
    unittest.main()
