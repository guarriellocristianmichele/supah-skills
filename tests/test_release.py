"""Tests for the repository rules scripts/release.py checks. Run: python -m unittest discover -s tests"""
import glob
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import release  # noqa: E402


class Copies(unittest.TestCase):
    def test_every_copy_of_learn_and_the_scanners_equals_its_source(self):
        self.assertEqual(release.check_scanner_copy(), [])


class Paragraphs(unittest.TestCase):
    def test_every_skill_carries_the_three_shared_paragraphs_in_order(self):
        for path in glob.glob(os.path.join(ROOT, "skills", "*", "SKILL.md")):
            with open(path, encoding="utf-8") as f:
                text = f.read()
            with self.subTest(skill=os.path.basename(os.path.dirname(path))):
                at = [text.find(p) for p in (release.ASK_WITH_OPTIONS, release.NEXT_STEP, release.LESSONS)]
                self.assertNotIn(-1, at)
                self.assertEqual(at, sorted(at))


if __name__ == "__main__":
    unittest.main()
