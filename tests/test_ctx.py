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


if __name__ == "__main__":
    unittest.main()
