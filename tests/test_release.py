"""Tests for the repository rules scripts/release.py checks. Run: python -m unittest discover -s tests"""
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import release  # noqa: E402


class Copies(unittest.TestCase):
    def test_every_copy_of_learn_and_the_scanners_equals_its_source(self):
        self.assertEqual(release.check_scanner_copy(), [])


class ReadmeSweep(unittest.TestCase):
    def test_readme_exceptions_come_only_from_docs_readme_keep(self):
        # a root .slop-prose-keep.tsv must not silently exempt README hits (AGENTS.md)
        cmd = release.readme_sweep(["README.md"])
        self.assertIn("--no-repo-keep", cmd)
        self.assertEqual(cmd[cmd.index("--keep") + 1], release.KEEP)


class Paragraphs(unittest.TestCase):
    def test_every_skill_carries_the_three_shared_paragraphs_in_order(self):
        for path in glob.glob(os.path.join(ROOT, "skills", "*", "SKILL.md")):
            with open(path, encoding="utf-8") as f:
                text = f.read()
            with self.subTest(skill=os.path.basename(os.path.dirname(path))):
                at = [text.find(p) for p in (release.ASK_WITH_OPTIONS, release.NEXT_STEP, release.LESSONS)]
                self.assertNotIn(-1, at)
                self.assertEqual(at, sorted(at))

    @unittest.skipUnless(shutil.which("bash"), "bash not installed")
    def test_the_lessons_read_command_exits_0_when_the_file_is_missing(self):
        # a project without .supah/ made the read end the agent's Bash call with exit code 2
        found = re.search(r"`(sed [^`]*LESSONS\.md[^`]*)`", release.LESSONS)
        self.assertIsNotNone(found, "the Lessons paragraph names its read command")
        cmd = found.group(1).replace("<skill>", "ai-slop-design")
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as empty:
            run = subprocess.run(["bash", "-c", cmd], cwd=empty, capture_output=True, text=True)
            self.assertEqual((run.returncode, run.stdout), (0, ""))
            os.mkdir(os.path.join(empty, ".supah"))
            with open(os.path.join(empty, ".supah", "LESSONS.md"), "w", encoding="utf-8") as f:
                f.write("## ai-slop-design-extra\n- no\n## ai-slop-design\n- yes\n## orchestrate\n- no\n")
            run = subprocess.run(["bash", "-c", cmd], cwd=empty, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0)
            self.assertIn("- yes", run.stdout)
            self.assertNotIn("- no", run.stdout)


if __name__ == "__main__":
    unittest.main()
