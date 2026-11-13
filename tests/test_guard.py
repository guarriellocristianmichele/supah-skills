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


def run(command, event=None):
    env = dict(os.environ, SUPAH_PROSE_HOME=HOME)
    data = json.dumps(event) if event is not None else ""
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

    def test_skips_code_and_agent_documents(self):
        skill = os.path.join(HOME, "skill")
        os.makedirs(skill, exist_ok=True)
        open(os.path.join(skill, "SKILL.md"), "w").close()
        for path in ("app.py", "SKILL.md", "AGENTS.md", os.path.join(".claude", "notes.md"),
                     os.path.join("skill", "TELLS.md")):
            with self.subTest(path=path):
                self.assertEqual(run("post", write(os.path.join(HOME, path), SLOP)).returncode, 0)

    def test_readme_next_to_skill_is_scanned(self):
        os.makedirs(os.path.join(HOME, "skill"), exist_ok=True)
        open(os.path.join(HOME, "skill", "SKILL.md"), "w").close()
        self.assertEqual(run("post", write(os.path.join(HOME, "skill", "README.md"), SLOP)).returncode, 2)


if __name__ == "__main__":
    unittest.main()
