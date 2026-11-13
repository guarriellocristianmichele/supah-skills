"""Tests for skills/orchestrate/scripts/mem.py. Run: python -m unittest discover -s tests"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM = os.path.join(ROOT, "skills", "orchestrate", "scripts", "mem.py")


def run(*args):
    return subprocess.run([sys.executable, MEM, *args], capture_output=True, text=True, timeout=60)


def state(d, **fields):
    with open(os.path.join(d, "state.json"), "w", encoding="utf-8") as f:
        json.dump(fields, f)


RUNNING = [
    {"id": "w1", "status": "running", "started": "2026-11-13T10:00"},
    {"id": "w2", "status": "running", "started": "2026-11-13T10:05"},
    {"id": "w0", "status": "done", "started": "2026-11-13T09:00"},
]


class Status(unittest.TestCase):
    def test_reports_budget(self):
        out = run("status", "--profile", "build", "--max", "3")
        data = json.loads(out.stdout)
        self.assertEqual(set(data), {"avail_mb", "total_mb", "reserve_mb", "per_agent_mb", "slots"})
        self.assertEqual(data["per_agent_mb"], 1500)
        self.assertLessEqual(data["slots"], 3)
        self.assertGreater(data["total_mb"], 0)


class Watch(unittest.TestCase):
    def test_idle_when_nothing_runs(self):
        with tempfile.TemporaryDirectory() as d:
            state(d, workers=[{"id": "w0", "status": "done"}])
            out = run("watch", "--state", d)
            self.assertEqual(out.returncode, 0)
            self.assertEqual(json.loads(out.stdout)["event"], "idle")

    def test_pressure_stops_newest_first_then_hard_stop(self):
        with tempfile.TemporaryDirectory() as d:
            state(d, reserve_mb=10**9, per_agent_mb=10**9, workers=RUNNING)  # always under pressure
            out = run("watch", "--state", d, "--interval", "0.2")
            self.assertEqual(out.returncode, 3)
            self.assertEqual(json.loads(out.stdout)["stop"], ["w2"])
            self.assertTrue(os.path.exists(os.path.join(d, "stop", "w2")))
            self.assertFalse(os.path.exists(os.path.join(d, "stop", "w0")))
            out = run("watch", "--state", d, "--interval", "0.2", "--grace", "0.1")
            self.assertEqual(out.returncode, 4)
            self.assertIn("w2", json.loads(out.stdout)["workers"])


if __name__ == "__main__":
    unittest.main()
