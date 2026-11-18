"""Tests for skills/context-audit/scripts/ctx.py. Run: python -m unittest discover -s tests"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CTX = os.path.join(ROOT, "skills", "context-audit", "scripts", "ctx.py")


def put(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content if isinstance(content, str) else json.dumps(content))


def load(path):
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def attachment(a):
    return json.dumps({"type": "attachment", "attachment": a})


class Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.home = os.path.join(cls.tmp, "home")
        cls.project = os.path.join(cls.tmp, "proj")
        slug = re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(cls.project))
        put(os.path.join(cls.project, "CLAUDE.md"), "@AGENTS.md\n")
        put(os.path.join(cls.project, "AGENTS.md"),
            "- Always run `scripts/release.py` before a commit (ADR 0001, ADR 0042).\n"
            "- Keep `docs/gone.md` short.\n- Plain line.\n")
        put(os.path.join(cls.project, "scripts", "release.py"), "")
        put(os.path.join(cls.project, "docs", "adr", "0001-x.md"), "# x\n")
        memory = os.path.join(cls.home, "projects", slug, "memory")
        put(os.path.join(memory, "MEMORY.md"), "- [A](a.md) — a\n- [Gone](gone.md) — b\n")
        put(os.path.join(memory, "a.md"), "---\nname: a\n---\nNever push on Fridays. See [[b-missing]].\n")
        put(os.path.join(memory, "orphan.md"), "---\nname: orphan\n---\nx\n")
        plugin = os.path.join(cls.home, "plugins", "cache", "m", "loud", "1.0")
        put(os.path.join(plugin, ".claude-plugin", "plugin.json"),
            {"name": "loud", "hooks": {"UserPromptSubmit": [{"hooks": [{"type": "command", "command": "x"}]}]}})
        put(os.path.join(cls.home, "plugins", "installed_plugins.json"),
            {"version": 2, "plugins": {"loud@m": [{"installPath": plugin}]}})
        put(os.path.join(cls.home, "settings.json"), {"enabledPlugins": {"loud@m": True}})
        listing = ("- alpha:tdd: Test-driven development with red-green-refactor.\n"
                   "- beta:test-driven-development: Use when implementing any feature, before code.\n"
                   "- simplify: Review the changed code for reuse.")
        lines = [
            json.dumps({"type": "user", "message": {"content": "secret prompt text"}}),
            attachment({"type": "skill_listing", "content": listing}),
            attachment({"type": "deferred_tools_delta", "addedLines": ["mcp__srv__tool_one", "mcp__srv__tool_two"]}),
            attachment({"type": "hook_success", "hookEvent": "SessionStart", "content": "RULES: you MUST be brief.\n" * 40}),
            attachment({"type": "hook_additional_context", "hookEvent": "UserPromptSubmit", "content": ["REMINDER be brief"]}),
            json.dumps({"type": "assistant", "message": {"usage": {
                "input_tokens": 10, "cache_creation_input_tokens": 3000, "cache_read_input_tokens": 990}}}),
            json.dumps({"type": "user", "message": {"content": "second prompt"}}),
            attachment({"type": "hook_additional_context", "hookEvent": "UserPromptSubmit", "content": ["REMINDER be brief"]}),
            "not json",
        ]
        put(os.path.join(cls.home, "projects", slug, "s1.jsonl"), "\n".join(lines) + "\n")

    def run_ctx(self, *args):
        out = subprocess.run([sys.executable, CTX, *args, "--home", self.home, "--project", self.project, "--json"],
                             capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertNotIn("secret prompt", out.stdout)
        return json.loads(out.stdout)


class Measure(Fixture):
    def test_first_request_is_measured_and_split(self):
        s = self.run_ctx("measure")[0]
        self.assertEqual(s["first_request_tokens"], 4000)
        self.assertEqual(s["prompts"], 2)
        categories = {b["category"]: b for b in s["breakdown"]}
        self.assertEqual({o["owner"] for o in categories["skill listing"]["by_owner"]},
                         {"alpha", "beta", "(built-in or user)"})
        self.assertEqual(categories["deferred tool names"]["by_owner"][0]["owner"], "srv")
        hooks = {h["source"].split(":")[0]: h for h in s["hooks"]}
        self.assertEqual(hooks["UserPromptSubmit"]["times"], 2)
        self.assertEqual(hooks["SessionStart"]["est_tokens"], round(26 * 40 / 4))
        self.assertLess(s["unattributed_tokens"], 4000)


class Sources(Fixture):
    def test_follows_imports_and_finds_always_on_hooks(self):
        data = self.run_ctx("sources")
        names = [os.path.basename(r["source"]) for r in data["sources"]]
        self.assertIn("AGENTS.md", names)
        self.assertIn("MEMORY.md", names)
        self.assertEqual(data["always_on_hooks"], {"loud@m": ["UserPromptSubmit"]})


class Check(Fixture):
    def test_memory_problems(self):
        kinds = {(f["kind"], f["where"], f["what"]) for f in self.run_ctx("check")["memory"]}
        self.assertEqual(kinds, {("index-missing-file", "MEMORY.md", "gone.md"),
                                 ("memory-not-indexed", "orphan.md", ""),
                                 ("dangling-memory-link", "a.md", "b-missing")})

    def test_missing_paths_and_adrs(self):
        found = {(f["kind"], f["what"]) for f in self.run_ctx("check")["references"]}
        self.assertEqual(found, {("missing-path", "docs/gone.md"), ("missing-adr", "ADR 0042")})

    def test_overlapping_skills_by_topic(self):
        groups = {g["topic"]: g["skills"] for g in self.run_ctx("check")["overlapping_skills"]}
        self.assertEqual(groups, {"test-driven development": ["alpha:tdd", "beta:test-driven-development"]})

    def test_rule_lines_include_hook_text(self):
        rules = self.run_ctx("check")["rules"]
        where = {r["where"] for r in rules}
        self.assertIn("AGENTS.md", where)
        self.assertIn("a.md", where)
        self.assertIn("hook SessionStart", where)
        self.assertNotIn("Plain line.", [r["text"] for r in rules])


class Sandbox(unittest.TestCase):
    """A fresh home and project per test, for cases the shared fixture cannot hold."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.home = os.path.join(self.tmp, "home")
        self.project = os.path.join(self.tmp, "proj")
        os.makedirs(self.home)
        os.makedirs(self.project)
        self.slug = re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(self.project))

    def transcript(self, name, lines, mtime=None):
        path = os.path.join(self.home, "projects", self.slug, name + ".jsonl")
        put(path, "\n".join(lines) + "\n")
        if mtime is not None:
            os.utime(path, (mtime, mtime))
        return path

    def ctx(self, *args):
        return subprocess.run([sys.executable, CTX, *args], capture_output=True, text=True,
                              encoding="utf-8", timeout=60)

    def ctx_json(self, *args):
        out = self.ctx(*args, "--home", self.home, "--project", self.project, "--json")
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)


class ImperativeRules(Sandbox):
    def test_imperative_lines_and_prompt_hook_text_are_rules(self):
        put(os.path.join(self.project, "AGENTS.md"),
            "# Style\n\nDrop articles and filler.\n- Write terse fragments.\n- Plain line.\nThe build is slow.\n")
        self.transcript("s1", [attachment({"type": "hook_additional_context", "hookEvent": "UserPromptSubmit",
                                           "content": ["CAVEMAN MODE ACTIVE (full). Fragments OK."]})])
        rules = self.ctx_json("check")["rules"]
        texts = [r["text"] for r in rules]
        self.assertIn("Drop articles and filler.", texts)
        self.assertIn("- Write terse fragments.", texts)
        self.assertNotIn("- Plain line.", texts)
        self.assertNotIn("The build is slow.", texts)
        self.assertNotIn("# Style", texts)
        self.assertIn(("hook UserPromptSubmit", "CAVEMAN MODE ACTIVE (full). Fragments OK."),
                      [(r["where"], r["text"]) for r in rules])


    def test_statements_that_open_with_a_verb_shaped_word_are_not_rules(self):
        orders = ["Drop articles and filler.", "- Write terse fragments.",
                  "Invoke a skill before any response.", "Usa frasi brevi.", "Non usare il grassetto.",
                  "Scrivi i commit in inglese.", "1. Keep the diff small."]
        statements = ["No transcripts are kept here.", "Return values are cached.", "Read more in the docs.",
                      "Non è un problema.", "Setup notes: run times vary by machine.",
                      "The cache is warm; keep reading for details.", "No, the build is fine."]
        put(os.path.join(self.project, "AGENTS.md"), "\n".join(orders + statements) + "\n")
        texts = [r["text"] for r in self.ctx_json("check")["rules"]]
        for line in orders:
            self.assertIn(line, texts)
        for line in statements:
            self.assertNotIn(line, texts)


class HookRows(Sandbox):
    def plugin(self, name, hooks):
        root = os.path.join(self.home, "plugins", "cache", "m", name, "1.0")
        put(os.path.join(root, "hooks", "hooks.json"), {"hooks": hooks})
        installed = os.path.join(self.home, "plugins", "installed_plugins.json")
        data = load(installed) or {"plugins": {}}
        data["plugins"][name + "@m"] = [{"installPath": root}]
        put(installed, data)
        settings = os.path.join(self.home, "settings.json")
        cfg = load(settings) or {"enabledPlugins": {}}
        cfg["enabledPlugins"][name + "@m"] = True
        put(settings, cfg)

    def test_fires_are_counted_not_prompts_and_cost_per_fire_is_given(self):
        hook = attachment({"type": "hook_additional_context", "hookEvent": "UserPromptSubmit",
                           "content": ["x" * 40]})
        self.transcript("s1", [json.dumps({"type": "user", "message": {"content": "only prompt"}}),
                               hook, hook, hook])
        s = self.ctx_json("measure")[0]
        self.assertEqual(s["prompts"], 1)
        row = s["hooks"][0]
        self.assertEqual(row["times"], 3)
        self.assertEqual(row["est_tokens_per_fire"], 10)
        self.assertEqual(row["est_tokens"], 30)

    def test_rows_name_the_plugin_that_ran_the_hook(self):
        self.plugin("loud", {"UserPromptSubmit": [{"hooks": [
            {"type": "command", "command": "node \"${CLAUDE_PLUGIN_ROOT}/t.js\"", "statusMessage": "Being loud..."}]}]})
        self.plugin("quiet", {"SessionStart": [{"hooks": [
            {"type": "command", "command": "\"${CLAUDE_PLUGIN_ROOT}/hooks/q.cmd\" start"}]}]})
        self.transcript("s1", [
            # plain stdout: the transcript records the status message as the command
            attachment({"type": "hook_success", "hookEvent": "SessionStart", "command": "Being loud...",
                        "content": "LOUD ON"}),
            # JSON stdout: the text comes back in a separate attachment that names no command
            attachment({"type": "hook_success", "hookEvent": "SessionStart", "content": "",
                        "command": "\"${CLAUDE_PLUGIN_ROOT}/hooks/q.cmd\" start",
                        "stdout": json.dumps({"hookSpecificOutput": {"additionalContext": "QUIET RULES"}})}),
            attachment({"type": "hook_additional_context", "hookEvent": "SessionStart", "content": ["QUIET RULES"]}),
            # no command at all: the only enabled plugin with a UserPromptSubmit hook ran it
            attachment({"type": "hook_additional_context", "hookEvent": "UserPromptSubmit", "content": ["LOUD TICK"]}),
            # an absolute path names its plugin folder
            attachment({"type": "hook_success", "hookEvent": "SessionStart", "content": "ABS",
                        "command": "bash /h/.claude/plugins/cache/mkt/abs-plugin/2.0/hooks/a.sh"}),
        ])
        owners = {h["source"]: h["owner"] for h in self.ctx_json("measure")[0]["hooks"]}
        self.assertEqual(owners, {"SessionStart: LOUD ON": "loud", "SessionStart: QUIET RULES": "quiet",
                                  "UserPromptSubmit: LOUD TICK": "loud", "SessionStart: ABS": "abs-plugin"})

    def test_a_plugin_named_in_the_text_breaks_a_tie(self):
        for name in ("caveman", "other"):
            self.plugin(name, {"UserPromptSubmit": [{"hooks": [{"type": "command", "command": name}]}]})
        self.transcript("s1", [
            attachment({"type": "hook_additional_context", "hookEvent": "UserPromptSubmit",
                        "content": ["CAVEMAN MODE ACTIVE. Drop articles."]}),
            attachment({"type": "hook_additional_context", "hookEvent": "UserPromptSubmit",
                        "content": ["Anonymous reminder."]})])
        owners = {h["source"]: h["owner"] for h in self.ctx_json("measure")[0]["hooks"]}
        self.assertEqual(owners, {"UserPromptSubmit: CAVEMAN MODE ACTIVE. Drop articles.": "caveman",
                                  "UserPromptSubmit: Anonymous reminder.": "?"})


class Sessions(Sandbox):
    def test_check_reads_hook_text_from_every_measured_session(self):
        self.transcript("old", [attachment({"type": "hook_additional_context", "hookEvent": "SessionStart",
                                            "content": ["Always reply in Latin."]})], mtime=1000)
        self.transcript("new", [attachment({"type": "hook_additional_context", "hookEvent": "SessionStart",
                                            "content": ["Never reply in Greek."]})], mtime=2000)
        texts = [r["text"] for r in self.ctx_json("check")["rules"]]
        self.assertIn("Always reply in Latin.", texts)
        self.assertIn("Never reply in Greek.", texts)
        texts = [r["text"] for r in self.ctx_json("check", "--sessions", "1")["rules"]]
        self.assertEqual(texts, ["Never reply in Greek."])

    def test_sessions_must_be_positive(self):
        self.transcript("s1", [attachment({"type": "skill_listing", "content": "- a: b"})])
        for bad in ("-1", "0"):
            out = self.ctx("measure", "--sessions", bad, "--home", self.home, "--project", self.project)
            self.assertNotEqual(out.returncode, 0)
            self.assertIn("--sessions", out.stderr)


class NothingToRead(Sandbox):
    def assert_one_line_failure(self, out, *words):
        self.assertNotIn(out.returncode, (0, None))
        lines = (out.stdout + out.stderr).strip().splitlines()
        self.assertEqual(len(lines), 1, lines)
        for w in words:
            self.assertIn(w, lines[0])

    def test_measure_without_transcripts_says_so(self):
        out = self.ctx("measure", "--home", self.home, "--project", self.project)
        self.assert_one_line_failure(out, "no transcripts")

    def test_missing_project_says_so(self):
        gone = os.path.join(self.tmp, "nope")
        for cmd in ("measure", "sources", "check"):
            self.assert_one_line_failure(self.ctx(cmd, "--home", self.home, "--project", gone), "nope")

    def test_missing_home_says_so(self):
        gone = os.path.join(self.tmp, "no-home")
        for cmd in ("measure", "sources", "check"):
            self.assert_one_line_failure(self.ctx(cmd, "--home", gone, "--project", self.project), "no-home")

    def test_check_works_without_transcripts(self):
        put(os.path.join(self.project, "AGENTS.md"), "- Always test.\n")
        self.assertEqual([r["text"] for r in self.ctx_json("check")["rules"]], ["- Always test."])


class SkillText(unittest.TestCase):
    def test_hook_cost_uses_fires_and_fixes_offer_none(self):
        with open(os.path.join(ROOT, "skills", "context-audit", "SKILL.md"), encoding="utf-8") as f:
            text = f.read()
        self.assertNotIn("× prompts", text)
        self.assertIn("apply none", text)


if __name__ == "__main__":
    unittest.main()
