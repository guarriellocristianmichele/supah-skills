"""Tests for skills/supah-help, the router over the supah skills. Run: python -m unittest discover -s tests"""
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Commands whose state stays on disk for the next command to read (ADR 0017): the ledger
# skills by name, and their modes written bare after the first command of a sequence.
LEDGER_SKILLS = ("/ai-slop-audit", "/ai-slop-design", "/buyer-panel")
BARE_MODES = ("audit", "plan", "publish", "fix", "verify", "sweep", "craft", "price", "pitch", "ground")
SEQUENCE = re.compile(r"\bthen\b|→|\band\b")


def doc(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def router(name):
    return doc("skills", "supah-help", name)


def situations(text):
    """The rows of the situations tables, each as its list of cells."""
    if "## Situations" in text:
        text = text.split("## Situations", 1)[1].split("\n## ", 1)[0]
    else:
        text = text.split("## What it recommends", 1)[1].split("\n## ", 1)[0]
    rows = []
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.startswith("|") and not set(cells[0]) <= set("-: ") and cells[0] not in ("You are…", "Situation"):
            rows.append(cells)
    return rows


def leaves_state(command):
    first = command.split()[0] if command.split() else ""
    return first in LEDGER_SKILLS or first in BARE_MODES


class Rows(unittest.TestCase):
    def test_router_has_a_row_for_skills_that_learn_from_the_user(self):
        for name in ("SKILL.md", "README.md"):
            rows = [r for r in situations(router(name)) if "learn" in r[0] and "correct" in r[0]]
            self.assertEqual(len(rows), 1, name)
            self.assertIn(".supah/LESSONS.md", rows[0][1], name)
            self.assertIn("verdict", rows[0][1], name)

    def test_router_has_a_row_for_grounding_a_panel_on_real_results(self):
        for name in ("SKILL.md", "README.md"):
            rows = [r for r in situations(router(name))
                    if "`/buyer-panel ground`" in r[1] and "`/buyer-panel test`" not in r[1]]
            self.assertEqual(len(rows), 1, name)
            self.assertIn("real", rows[0][0], name)


class Clear(unittest.TestCase):
    def test_every_sequence_of_ledger_commands_has_clear_between_them(self):
        for name in ("SKILL.md", "README.md"):
            for row in situations(router(name)):
                parts = re.split(r"`([^`]*)`", row[1])
                commands = [(i, parts[i]) for i in range(1, len(parts), 2)
                            if leaves_state(parts[i]) or parts[i] == "/clear"]
                for (i, a), (j, b) in zip(commands, commands[1:]):
                    if leaves_state(a) and leaves_state(b):
                        gap = "".join(parts[i + 1:j])
                        with self.subTest(file=name, situation=row[0][:40], pair=(a, b)):
                            self.assertIsNone(SEQUENCE.search(gap), gap)

    def test_every_follow_up_of_a_ledger_run_starts_with_clear(self):
        for name in ("SKILL.md", "README.md"):
            for row in situations(router(name)):
                commands = re.findall(r"`([^`]*)`", row[1])
                follow_up = "after " in row[0] + row[1] or row[0].startswith("holding")
                if follow_up and any(leaves_state(c) for c in commands):
                    with self.subTest(file=name, situation=row[0][:40]):
                        self.assertIn("/clear", commands)

    def test_the_sequence_check_catches_a_missing_clear(self):
        parts = re.split(r"`([^`]*)`", "`fix all` (or `fix B1`, one batch at a time, then `verify`)")
        self.assertTrue(leaves_state(parts[3]) and leaves_state(parts[5]))
        self.assertIsNotNone(SEQUENCE.search(parts[4]))


class NoArguments(unittest.TestCase):
    def test_situations_are_grouped_into_two_to_four_choices(self):
        section = router("SKILL.md").split("## Situations", 1)[1].split("\n## ", 1)[0]
        groups = re.findall(r"^### (.+)$", section, re.M)
        self.assertGreaterEqual(len(groups), 2)
        self.assertLessEqual(len(groups), 4)
        for chunk in section.split("\n### ")[1:]:
            self.assertTrue(situations("## Situations\n" + chunk), chunk.splitlines()[0])
        self.assertEqual(section.split("\n### ", 1)[0].count("\n|"), 0, "every row sits under a group")

    def test_no_arguments_asks_for_a_group_before_showing_rows(self):
        intro = router("SKILL.md").split("**Ask with options.**", 1)[0]
        empty = intro.split("`$ARGUMENTS` is empty", 1)[1]
        self.assertIn("group", empty.split(".", 1)[0])
        self.assertIn("group", router("README.md").split("With no arguments", 1)[1].split(".", 1)[0])


class Uncovered(unittest.TestCase):
    def test_a_situation_no_skill_covers_is_said_and_pointed_elsewhere(self):
        text = router("SKILL.md")
        rule = [p for p in text.split("\n\n") if "no skill" in p and "Boundaries" in p]
        self.assertEqual(len(rule), 1)
        self.assertIn("outside", rule[0])


if __name__ == "__main__":
    unittest.main()
