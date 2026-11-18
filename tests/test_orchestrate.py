"""Structural checks on skills/orchestrate/SKILL.md and its README: the procedure a resume and a
watchdog failure depend on. Run: python -m unittest discover -s tests"""
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def doc(*parts):
    with open(os.path.join(ROOT, "skills", "orchestrate", *parts), encoding="utf-8") as f:
        return f.read()


def section(text, heading):
    """The body under `## heading`, up to the next `## ` outside a code fence."""
    body, fenced = [], False
    for line in text.split("\n## " + heading + "\n", 1)[1].splitlines():
        if line.startswith("```"):
            fenced = not fenced
        elif line.startswith("## ") and not fenced:
            break
        body.append(line)
    return "\n".join(body)


def step(text, name):
    """The numbered step `N. **name**` of the Steps section, up to the next numbered step."""
    match = re.search(r"^\d+\. \*\*" + name + r"\.?\*\*(.*?)(?=^\d+\. \*\*|^\*\*Completion|\Z)",
                      section(text, "Steps"), re.S | re.M)
    return match.group(1)


SKILL = doc("SKILL.md")


class JobRecord(unittest.TestCase):
    def test_the_job_is_saved_so_a_resume_after_clear_does_not_ask_again(self):
        state = section(SKILL, "State")
        self.assertIn("`job.md`", state)
        for field in ("brief", "done criterion", "profile", "writes"):
            self.assertIn(field, state.split("`job.md`", 1)[1].split("\n- ", 1)[0])
        self.assertIn("job.md", SKILL.split("## State", 1)[0], "the intro must not ask for what job.md holds")
        self.assertIn("job.md", step(SKILL, "Resume"))

    def test_inline_work_has_a_worker_id_and_its_own_work_file(self):
        size = step(SKILL, "Size")
        self.assertIn("`inline`", size)
        self.assertIn("`assigned:inline`", size)
        self.assertIn("`work/inline.md`", size)


class StoppedBlocks(unittest.TestCase):
    def test_a_block_with_nothing_remaining_closes_and_completion_accepts_it(self):
        self.assertIn("Status: closed", section(SKILL, "STOPPED_AGENTS_WORK.md block"))
        completion = SKILL.split("**Completion.**", 1)[1].split("\n", 1)[0]
        self.assertIn("`resumed as <id>` or `closed`", completion)

    def test_only_remaining_units_without_a_checkpoint_go_back_to_pending(self):
        resume = step(SKILL, "Resume")
        self.assertNotIn("Units of `open` STOPPED blocks go back to `pending`", resume)
        self.assertIn("`Remaining`", resume)
        self.assertIn("`Done` units stay `done`", resume)


class WatchdogError(unittest.TestCase):
    def test_react_has_a_branch_for_exit_1(self):
        react = step(SKILL, "React")
        self.assertIn("**Watchdog exit 1**", react)
        self.assertIn('"error"', react)

    def test_the_readme_lists_exit_1_in_both_languages(self):
        readme = doc("README.md")
        english, italian = readme.split("## Italiano", 1)
        self.assertRegex(english, r"\| 1 \| [^|]*state\.json[^|]* \| `\{\"event\": \"error\"")
        self.assertRegex(italian, r"`1` [^;]*`state\.json`")


if __name__ == "__main__":
    unittest.main()
