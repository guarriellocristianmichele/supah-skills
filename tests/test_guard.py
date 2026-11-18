"""Tests for plugins/slop-guard/hooks/guard.py. Run: python -m unittest discover -s tests"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(ROOT, "plugins", "slop-guard", "hooks", "guard.py")
HOME = tempfile.mkdtemp()  # empty learned model, so results don't depend on the machine's verdicts
SLOP = "This isn't about speed. It's about trust. I hope this helps — let me know!\n"


def run(command, event=None, raw=None):
    env = dict(os.environ, SUPAH_PROSE_HOME=HOME)
    data = raw if raw is not None else json.dumps(event) if event is not None else ""
    return subprocess.run([sys.executable, GUARD, command], input=data, capture_output=True,
                          text=True, encoding="utf-8", env=env, timeout=60)


def write(path, content):
    return {"tool_name": "Write", "tool_input": {"file_path": path, "content": content}}


class Session(unittest.TestCase):
    def test_prints_rules_within_token_budget(self):
        out = run("session")
        self.assertEqual(out.returncode, 0)
        self.assertIn("slop-guard", out.stdout)
        self.assertLess(len(out.stdout), 800, "rules are injected every session: keep them short")


class Post(unittest.TestCase):
    def test_reports_tells_in_one_line(self):
        out = run("post", write(os.path.join(HOME, "notes.md"), SLOP))
        self.assertEqual(out.returncode, 2)
        self.assertEqual(out.stdout, "")
        self.assertEqual(len(out.stderr.strip().splitlines()), 1)
        for rule in ("chat-residue", "em-dash"):
            self.assertIn(rule, out.stderr)
        self.assertIn("—", out.stderr)

    def test_silent_on_clean_prose(self):
        out = run("post", write(os.path.join(HOME, "notes.md"), "The cache keeps the last ten results.\n"))
        self.assertEqual((out.returncode, out.stdout, out.stderr), (0, "", ""))

    def test_edit_scans_only_the_new_text(self):
        event = {"tool_name": "Edit", "tool_input": {"file_path": os.path.join(HOME, "notes.md"),
                                                      "old_string": SLOP, "new_string": "The cache is small.\n"}}
        self.assertEqual(run("post", event).returncode, 0)

    def test_multiedit_scans_every_new_string(self):
        event = {"tool_name": "MultiEdit", "tool_input": {"file_path": os.path.join(HOME, "notes.md"),
                                                           "edits": [{"old_string": "a", "new_string": "Fine."},
                                                                     {"old_string": "b", "new_string": SLOP}]}}
        self.assertEqual(run("post", event).returncode, 2)

    def test_skips_other_files_and_agent_documents(self):
        skill = os.path.join(HOME, "skill")
        os.makedirs(skill, exist_ok=True)
        open(os.path.join(skill, "SKILL.md"), "w").close()
        for path in ("data.csv", "SKILL.md", "AGENTS.md", os.path.join(".claude", "notes.md"),
                     os.path.join("skill", "TELLS.md")):
            with self.subTest(path=path):
                self.assertEqual(run("post", write(os.path.join(HOME, path), SLOP)).returncode, 0)

    def test_code_reports_hits_on_the_new_lines_only(self):
        path = os.path.join(HOME, "app.py")
        old = "def parse(raw):\n    try:\n        return int(raw)\n    except ValueError as e:\n        raise e\n"
        added = "\n\ndef double(x):\n    # Return the double\n    return x * 2\n"
        with open(path, "w", encoding="utf-8") as f:
            f.write(old + added)
        edit = {"tool_name": "Edit", "tool_input": {"file_path": path, "old_string": "", "new_string": added}}
        out = run("post", edit)
        self.assertEqual(out.returncode, 2)
        self.assertIn("restating-comment", out.stderr)
        self.assertNotIn("catch-rethrow", out.stderr)  # written earlier, not by this edit
        out = run("post", write(path, old + added))
        self.assertIn("catch-rethrow", out.stderr)

    def test_clean_code_is_silent(self):
        path = os.path.join(HOME, "clean.ts")
        text = "export function area(w: number, h: number) {\n  return w * h;\n}\n"
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        out = run("post", write(path, text))
        self.assertEqual((out.returncode, out.stderr), (0, ""))

    def test_readme_next_to_skill_is_scanned(self):
        os.makedirs(os.path.join(HOME, "skill"), exist_ok=True)
        open(os.path.join(HOME, "skill", "SKILL.md"), "w").close()
        self.assertEqual(run("post", write(os.path.join(HOME, "skill", "README.md"), SLOP)).returncode, 2)


class MalformedInput(unittest.TestCase):
    """A hook that crashes prints a traceback into the session; bad input is not the writer's slop."""

    def assertSilent(self, out):
        self.assertEqual((out.returncode, out.stdout, out.stderr), (0, "", ""))

    def test_empty_stdin_is_silent(self):
        self.assertSilent(run("post"))

    def test_malformed_json_is_silent(self):
        self.assertSilent(run("post", raw='{"tool_name": "Write", "tool_input": {'))

    def test_json_array_is_silent(self):
        self.assertSilent(run("post", [write(os.path.join(HOME, "notes.md"), SLOP)]))

    def test_fields_of_the_wrong_type_are_silent(self):
        notes = os.path.join(HOME, "notes.md")
        for tool_input in ("notes.md", ["notes.md"], {"file_path": 7, "content": SLOP},
                           {"file_path": notes, "content": 7}, {"file_path": notes, "content": None},
                           {"file_path": notes, "edits": "Fine."}, {"file_path": notes, "edits": [SLOP]},
                           {"file_path": notes, "edits": [{"new_string": 7}]},
                           {"file_path": notes, "new_string": ["Fine."]}):
            with self.subTest(tool_input=tool_input):
                self.assertSilent(run("post", {"tool_name": "Write", "tool_input": tool_input}))


if __name__ == "__main__":
    unittest.main()
