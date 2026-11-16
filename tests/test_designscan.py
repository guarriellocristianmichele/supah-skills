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


def doc(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


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


PLATFORMS = os.path.join(FIX, "platforms")


def inventory(name):
    root = os.path.join(PLATFORMS, name)
    out = run("surfaces", root)
    data = json.loads(out.stdout)
    rel = lambda f: os.path.relpath(f, root).replace("\\", "/")  # noqa: E731
    units = {u["unit"]: (u["kind"], sorted(rel(f) for f in u["files"])) for u in data["units"]}
    return data, units, out.returncode


class Surfaces(unittest.TestCase):
    """The inventory an audit fans out over: every frontend file in exactly one unit."""

    def test_next_routes_own_their_components_and_shared_takes_the_rest(self):
        data, units, code = inventory("next")
        self.assertEqual((code, data["framework"], data["fallback"]), (0, "nextjs", None))
        self.assertEqual(units, {
            "/": ("route", ["app/Hero.tsx", "app/page.tsx"]),
            "/about": ("route", ["app/(marketing)/about/page.tsx"]),
            "/pricing": ("route", ["app/pricing/PlanCard.tsx", "app/pricing/page.tsx"]),
            "shared": ("shared", ["app/globals.css", "app/layout.tsx", "components/Button.tsx",
                                  "components/Unused.tsx", "next.config.mjs"]),
        })
        shared = [u for u in data["units"] if u["kind"] == "shared"][0]
        self.assertEqual(sorted(os.path.basename(f) for f in shared["unreached"]), ["Unused.tsx", "next.config.mjs"])

    def test_sveltekit_layouts_reach_the_routes_below_them(self):
        data, units, code = inventory("sveltekit")
        self.assertEqual((code, data["framework"], data["fallback"]), (0, "sveltekit", None))
        self.assertEqual(units, {
            "/": ("route", ["src/routes/+page.svelte"]),
            "/about": ("route", ["src/routes/about/+page.svelte", "src/routes/about/+page.ts"]),
            "/dashboard": ("route", ["src/lib/Chart.svelte", "src/routes/(app)/+layout.svelte",
                                     "src/routes/(app)/dashboard/+page.svelte"]),
            "shared": ("shared", ["src/app.css", "src/lib/Card.svelte", "src/routes/+layout.svelte",
                                  "svelte.config.js"]),
        })

    def test_no_route_convention_falls_back_to_directories(self):
        data, units, code = inventory("plain")
        self.assertEqual((code, data["framework"], data["fallback"]), (0, None, "directories"))
        self.assertEqual(units, {
            ".": ("directory", ["main.js"]),
            "marketing": ("directory", ["marketing/Banner.vue"]),
            "styles": ("directory", ["styles/base.css"]),
            "widgets": ("directory", ["widgets/Clock.tsx", "widgets/Weather.tsx"]),
        })

    def tree(self, files):
        d = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, d)
        for name, text in files.items():
            os.makedirs(os.path.dirname(os.path.join(d, name)), exist_ok=True)
            write(d, name, text)
        out = run("surfaces", d)
        data = json.loads(out.stdout)
        rel = lambda f: os.path.relpath(f, d).replace("\\", "/")  # noqa: E731
        return data["framework"], {u["unit"]: sorted(rel(f) for f in u["files"]) for u in data["units"]}

    def test_nuxt_pages_reach_auto_imported_components_by_name(self):
        framework, units = self.tree({
            "package.json": '{"dependencies": {"nuxt": "3.13.0"}}',
            "app.vue": "<template><NuxtPage /></template>\n",
            "pages/index.vue": "<template><BaseButton /></template>\n",
            "pages/shop/[id].vue": "<template><base-button /><ProductGallery /></template>\n",
            "components/base/Button.vue": "<template><button /></template>\n",
            "components/ProductGallery.vue": "<template><div /></template>\n",
        })
        self.assertEqual((framework, units), ("nuxt", {
            "/": ["pages/index.vue"],
            "/shop/[id]": ["components/ProductGallery.vue", "pages/shop/[id].vue"],
            "shared": ["app.vue", "components/base/Button.vue"],
        }))

    def test_astro_pages_and_react_router_file_routes(self):
        framework, units = self.tree({
            "package.json": '{"dependencies": {"astro": "4.16.0"}}',
            "src/pages/index.astro": "---\nimport Base from '../layouts/Base.astro';\n---\n<Base />\n",
            "src/pages/blog/[slug].astro": "---\nimport Base from '../../layouts/Base.astro';\n---\n<Base />\n",
            "src/layouts/Base.astro": "<html><slot /></html>\n",
        })
        self.assertEqual((framework, units), ("astro", {
            "/": ["src/pages/index.astro"], "/blog/[slug]": ["src/pages/blog/[slug].astro"],
            "shared": ["src/layouts/Base.astro"]}))
        framework, units = self.tree({
            "package.json": '{"dependencies": {"react-router": "7.0.0"}}',
            "app/root.tsx": "export default function Root() { return null; }\n",
            "app/routes/_index.tsx": "import { Nav } from '~/components/Nav';\n",
            "app/routes/blog.$slug.tsx": "export default function Post() { return null; }\n",
            "app/components/Nav.tsx": "export function Nav() { return null; }\n",
        })
        self.assertEqual((framework, units), ("react-router", {
            "/": ["app/components/Nav.tsx", "app/routes/_index.tsx"], "/blog/:slug": ["app/routes/blog.$slug.tsx"],
            "shared": ["app/root.tsx"]}))

    def test_a_directory_above_the_unit_size_splits_and_vendored_files_are_left_out(self):
        with tempfile.TemporaryDirectory() as d:
            for sub in ("forms", "cards"):
                os.makedirs(os.path.join(d, "components", sub))
                for i in range(25):
                    write(os.path.join(d, "components", sub), "C%d.tsx" % i, "export {};\n")
            os.makedirs(os.path.join(d, "vendor"))
            write(os.path.join(d, "vendor"), "lib.js", "export {};\n")
            write(d, "app.min.js", "x;\n")
            out = run("surfaces", d)
            data = json.loads(out.stdout)
        sizes = {u["unit"]: len(u["files"]) for u in data["units"]}
        self.assertEqual(sizes, {"components/cards": 25, "components/forms": 25})
        self.assertEqual(sorted((os.path.basename(s["file"]), s["reason"]) for s in data["skipped"]),
                         [("app.min.js", "minified"), ("lib.js", "vendored or generated")])


class HitsFile(unittest.TestCase):
    """The audit writes its one scan to the ledger, grouped by unit, and each worker reads only its unit."""

    def test_hits_grouped_by_surface_match_a_plain_scan_of_the_same_files(self):
        with tempfile.TemporaryDirectory() as d:
            inv, hits = os.path.join(d, "surfaces.json"), os.path.join(d, "hits.json")
            run("surfaces", os.path.join(PLATFORMS, "next"), "--out", inv)
            out = run("--surfaces", inv, "--out", hits)
            with open(inv, encoding="utf-8") as f:
                units = json.load(f)["units"]
            with open(hits, encoding="utf-8") as f:
                grouped = json.load(f)
        files = [f for u in units for f in u["files"]]
        plain = json.loads(run("--json", *files).stdout)
        self.assertEqual(out.returncode, 1)
        self.assertEqual([(u["unit"], [r["file"] for r in u["files"]]) for u in grouped["units"]],
                         [(u["unit"], u["files"]) for u in units])
        self.assertEqual([r for u in grouped["units"] for r in u["files"]], plain)
        home = [u for u in grouped["units"] if u["unit"] == "/"][0]
        self.assertIn("gradient-text", {h["rule"] for r in home["files"] for h in r["hits"]})

    def test_a_worker_reads_its_unit_without_the_duplication_hits(self):
        with tempfile.TemporaryDirectory() as d:
            for sub, name in (("checkout", "dup-a.tsx"), ("account", "dup-b.tsx"), ("styles", "dup.css")):
                os.makedirs(os.path.join(d, sub))
                with open(os.path.join(FIX, name), encoding="utf-8") as f:
                    write(os.path.join(d, sub), name, f.read())
            inv, hits = os.path.join(d, "surfaces.json"), os.path.join(d, "hits.json")
            run("surfaces", d, "--out", inv)
            summary = run("--surfaces", inv, "--out", hits).stdout
            unit = run("hits", hits, "checkout")
            missing = run("hits", hits, "nowhere")
        self.assertIn("repeated-class-string", summary)
        results = json.loads(unit.stdout)
        self.assertEqual([os.path.basename(r["file"]) for r in results], ["dup-a.tsx"])
        self.assertNotIn("duplication", {h["category"] for r in results for h in r["hits"]})
        self.assertEqual(missing.returncode, 2)


class Docs(unittest.TestCase):
    def test_readme_states_the_rule_count(self):
        n = len(run("rules").stdout.splitlines()) - 2
        with open(os.path.join(ROOT, "skills", "ai-slop-design", "README.md"), encoding="utf-8") as f:
            self.assertIn("%d rules in" % n, f.read())

    def test_modes_table_lists_audit_with_its_file(self):
        with open(os.path.join(ROOT, "skills", "ai-slop-design", "SKILL.md"), encoding="utf-8") as f:
            rows = [line.split("|") for line in f if line.startswith("| `")]
        modes = {r[1].strip().split()[0].strip("`"): r[2].strip() for r in rows}
        self.assertEqual(modes.get("audit"), "`${CLAUDE_SKILL_DIR}/AUDIT.md`")
        self.assertTrue(os.path.exists(os.path.join(ROOT, "skills", "ai-slop-design", "AUDIT.md")))

    def test_craft_restyles_a_surface_and_keeps_its_content_and_behaviour(self):
        craft = doc("skills", "ai-slop-design", "CRAFT.md")
        restyle = craft.split("## Restyle", 1)[1]
        self.assertIn("`craft <surface>`", restyle)
        self.assertIn("brief is read from the surface", restyle)
        self.assertIn("content and behaviour unchanged", craft.split("**Completion.**", 1)[1])

    def test_restyle_direction_check_names_the_handoffs_lane(self):
        check = doc("skills", "ai-slop-design", "CRAFT.md").split("6. **Check the direction**", 1)[1].split("\n7. ", 1)[0]
        self.assertIn("the handoff's lane", check)

    def test_handoffs_point_at_craft_surface(self):
        self.assertIn("`craft <surface>`", doc("skills", "ai-slop-design", "SWEEP.md"))
        skill = doc("skills", "ai-slop-design", "SKILL.md")
        self.assertIn("| `craft <surface>` |", skill)
        self.assertIn("craft <surface>", skill.split("argument-hint:", 1)[1].split("\n", 1)[0])
        self.assertIn("`handoff` (the whole page sits in a lane and needs a new direction from `craft <surface>`", skill)

    def test_glossary_readme_and_router_name_the_restyle(self):
        self.assertIn("**Restyle**:", doc("GLOSSARY.md"))
        readme = doc("skills", "ai-slop-design", "README.md")
        english, italian = readme.split("## Italiano", 1)
        self.assertIn("craft <surface>", english)
        self.assertIn("craft <surface>", italian)
        for name in ("SKILL.md", "README.md"):
            self.assertIn("/ai-slop-design craft <surface>", doc("skills", "supah-help", name))


class DuplicationOwnership(unittest.TestCase):
    RULES = ("`repeated-class-string`", "`duplicate-css-block`", "`untokened-colour`")

    def test_code_audit_hands_frontend_duplication_to_the_design_ledger(self):
        audit = doc("skills", "ai-slop-audit", "AUDIT.md")
        step = audit.split("- **duplication (textual)**", 1)[1].split("\n- **", 1)[0]
        for rule in self.RULES:
            self.assertIn(rule, step)
        self.assertIn("`.slop-design/findings.md` exists", step)
        self.assertIn("`handoff:ai-slop-design`", step)

    def test_call_graph_has_a_one_way_edge_from_the_code_audit_to_the_design_ledger(self):
        adr = doc("docs", "adr", "0012-skills-reach-each-other-by-files-and-orchestrate.md")
        graph = adr.split("## Call graph", 1)[1].split("\n## ", 1)[0]
        edges = {line.split(" → ", 1)[0][2:]: line for line in graph.splitlines() if " → " in line}
        self.assertIn("ai-slop-design's ledger", edges["ai-slop-audit"])
        self.assertNotIn("ai-slop-audit", edges["ai-slop-design"])

    def test_design_companions_keep_component_work_in_the_design_audit(self):
        skill = doc("skills", "ai-slop-design", "SKILL.md")
        note = skill.split("- **ai-slop-audit**:", 1)[1].split("\n- **", 1)[0]
        self.assertIn("`handoff:ai-slop-design`", note)
        self.assertIn("token/component batch", note)
        self.assertIn("never calls it", note)

    def test_readme_glossary_and_router_name_the_handoff(self):
        english, italian = doc("skills", "ai-slop-audit", "README.md").split("## Italiano", 1)
        self.assertIn("handoff:ai-slop-design", english)
        self.assertIn("handoff:ai-slop-design", italian)
        self.assertIn("`handoff:ai-slop-design`", doc("GLOSSARY.md").split("**Handoff**:", 1)[1].split("\n\n", 1)[0])
        self.assertIn("`handoff:ai-slop-design`", doc("skills", "supah-help", "SKILL.md"))


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
