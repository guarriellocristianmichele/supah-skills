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

    def assert_clean_error(self, out, reason):
        self.assertEqual(out.returncode, 1)
        self.assertNotIn("Traceback", out.stderr)
        event = json.loads(out.stdout)
        self.assertEqual(event["event"], "error")
        self.assertIn(reason, event["error"])

    def test_a_missing_state_file_is_a_clean_error(self):
        with tempfile.TemporaryDirectory() as d:
            self.assert_clean_error(run("watch", "--state", d, "--interval", "0.05"), "state.json")
            self.assertFalse(os.path.exists(os.path.join(d, "stop")))

    def test_a_missing_state_dir_is_a_clean_error_and_is_not_created(self):
        with tempfile.TemporaryDirectory() as d:
            gone = os.path.join(d, "no-such-job")
            self.assert_clean_error(run("watch", "--state", gone, "--interval", "0.05"), "state.json")
            self.assertFalse(os.path.exists(gone))

    def test_a_half_written_state_file_is_a_clean_error(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "state.json"), "w", encoding="utf-8") as f:
                f.write('{"session": "s1", "workers": [{"id": "w1", "status": "runn')
            self.assert_clean_error(run("watch", "--state", d, "--interval", "0.05"), "unreadable")

    def test_a_state_file_that_is_not_a_job_state_is_a_clean_error(self):
        for body in ("[]", '{"workers": {"w1": "running"}}', '{"workers": ["w1"]}'):
            with self.subTest(body=body), tempfile.TemporaryDirectory() as d:
                with open(os.path.join(d, "state.json"), "w", encoding="utf-8") as f:
                    f.write(body)
                self.assert_clean_error(run("watch", "--state", d, "--interval", "0.05"), "not a job state")


if __name__ == "__main__":
    unittest.main()
