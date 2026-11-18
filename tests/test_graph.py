"""Tests for skills/orchestrate/scripts/graph.py. Run: python -m unittest discover -s tests"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAPH = os.path.join(ROOT, "skills", "orchestrate", "scripts", "graph.py")


def frontier(rows, header="| unit | status | blocked-by | files |"):
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "units.md"), "w", encoding="utf-8") as f:
            f.write(header + "\n|" + "---|" * (header.count("|") - 1) + "\n")
            for row in rows:
                f.write("| " + " | ".join(row) + " |\n")
        out = subprocess.run([sys.executable, GRAPH, "frontier", "--state", d],
                             capture_output=True, text=True, timeout=60)
    return out.returncode, json.loads(out.stdout)


class Frontier(unittest.TestCase):
    def test_pending_units_without_blockers_are_the_frontier(self):
        code, data = frontier([("B1", "done", "none", ""), ("B2", "pending", "none", ""),
                               ("B3", "assigned:w1", "none", ""), ("B4", "pending", "", "")])
        self.assertEqual(code, 0)
        self.assertEqual(data["frontier"], ["B2", "B4"])

    def test_a_unit_waits_until_every_blocker_is_done(self):
        code, data = frontier([("B1", "done", "none", ""), ("B2", "assigned:w1", "none", ""),
                               ("B3", "pending", "B1", ""), ("B4", "pending", "B1, B2", "")])
        self.assertEqual(data["frontier"], ["B3"])
        self.assertEqual(data["waiting"], {"B4": ["B2"]})

    def test_a_failed_unit_blocks_only_its_dependents_and_the_rest_go_on(self):
        code, data = frontier([("B1", "failed:checks red", "none", ""), ("B2", "pending", "B1", ""),
                               ("B3", "pending", "B2", ""), ("B4", "pending", "none", ""),
                               ("B5", "blocked:B9", "none", ""), ("B6", "pending", "B5", "")])
        self.assertEqual(data["frontier"], ["B4"])
        self.assertEqual(data["blocked"], {"B2": "B1", "B3": "B1", "B6": "B9"})
        self.assertEqual(data["waiting"], {})


class Overlap(unittest.TestCase):
    def test_units_sharing_a_file_run_in_plan_order(self):
        code, data = frontier([("B1", "pending", "none", "src/a.ts, src/b.ts"),
                               ("B2", "pending", "none", "src/b.ts"),
                               ("B3", "pending", "none", "src/c.ts")])
        self.assertEqual(data["frontier"], ["B1", "B3"])
        self.assertEqual(data["waiting"], {"B2": ["B1"]})
        self.assertEqual(data["implied"], {"B2": ["B1"]})

    def test_a_declared_blocker_sets_the_order_of_an_overlap(self):
        code, data = frontier([("B1", "pending", "B2", "src/a.ts"),
                               ("B2", "pending", "none", "src/a.ts")])
        self.assertEqual(code, 0)
        self.assertEqual(data["frontier"], ["B2"])
        self.assertEqual(data["implied"], {})

    def test_a_failed_unit_releases_the_units_it_only_overlaps(self):
        code, data = frontier([("B1", "failed:merge conflict", "none", "src/a.ts"),
                               ("B2", "pending", "none", "src/a.ts")])
        self.assertEqual(data["frontier"], ["B2"])
        self.assertEqual(data["blocked"], {})

    def test_a_unit_that_can_never_start_releases_the_units_it_only_overlaps(self):
        code, data = frontier([("B1", "failed:checks red", "none", "src/a.ts"),
                               ("B2", "pending", "B1", "src/b.ts"),
                               ("B3", "pending", "none", "src/b.ts")])
        self.assertEqual(data["blocked"], {"B2": "B1"})
        self.assertEqual(data["frontier"], ["B3"])


class Invalid(unittest.TestCase):
    def test_a_cycle_stops_the_job(self):
        code, data = frontier([("B1", "pending", "B3", ""), ("B2", "pending", "B1", ""),
                               ("B3", "pending", "B2", ""), ("B4", "pending", "none", "")])
        self.assertEqual(code, 2)
        self.assertEqual(data["cycle"], ["B1", "B3", "B2", "B1"])
        self.assertNotIn("frontier", data)

    def test_an_unknown_blocker_stops_the_job(self):
        code, data = frontier([("B1", "pending", "B7", "")])
        self.assertEqual(code, 2)
        self.assertEqual(data["unknown"], {"B1": ["B7"]})

    def test_a_table_without_blocker_columns_is_a_job_of_independent_units(self):
        code, data = frontier([("a.md", "pending"), ("b.md", "done"), ("c.md", "pending")],
                              header="| unit | status |")
        self.assertEqual((code, data["frontier"]), (0, ["a.md", "c.md"]))


if __name__ == "__main__":
    unittest.main()
