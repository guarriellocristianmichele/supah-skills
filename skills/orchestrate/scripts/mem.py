#!/usr/bin/env python3
"""Memory gauge and watchdog for the orchestrate skill. Stdlib only.

  mem.py status [--profile light|build] [--per-agent MB] [--reserve MB] [--max N]
      Print JSON: avail_mb, total_mb, reserve_mb, per_agent_mb, slots.

  mem.py watch --state DIR [--interval S] [--grace S]
      Watch DIR/state.json. Exit 0 when no worker is running.
      Exit 3 on memory pressure, after writing DIR/stop/<id> for the newest
      running workers that must shed (printed as JSON).
      Exit 4 when workers flagged earlier are still running after --grace
      seconds and pressure persists (hard stop needed).
      Exit 1 with {"event": "error", "error": ...} when state.json is missing,
      unreadable or not a job state after a few reads 0.2 s apart (a file
      caught mid-write is read again first).
"""
import argparse
import ctypes
import json
import math
import os
import platform
import subprocess
import sys
import time

PROFILES = {"light": 400, "build": 1500}  # MB per concurrent worker, before calibration


def memory_mb():
    """Return (available_mb, total_mb) for this machine."""
    system = platform.system()
    if system == "Windows":
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        return stat.ullAvailPhys // 2**20, stat.ullTotalPhys // 2**20
    if system == "Linux":
        info = {}
        with open("/proc/meminfo") as f:
            for line in f:
                key, value = line.split(":", 1)
                info[key] = int(value.split()[0])  # kB
        return info["MemAvailable"] // 1024, info["MemTotal"] // 1024
    if system == "Darwin":
        total = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"])) // 2**20
        out = subprocess.check_output(["vm_stat"], text=True)
        page = int(out.split("page size of")[1].split()[0])
        pages = {}
        for line in out.splitlines()[1:]:
            if ":" in line:
                key, value = line.split(":", 1)
                pages[key.strip()] = int(value.strip().rstrip("."))
        free = sum(pages.get(k, 0) for k in ("Pages free", "Pages inactive", "Pages speculative"))
        return free * page // 2**20, total
    sys.exit(f"unsupported platform: {system}")


def default_reserve(total_mb):
    return max(2048, int(total_mb * 0.15))


def slots(avail, reserve, per_agent, cap):
    return max(0, min(cap, (avail - reserve) // per_agent))


class StateError(Exception):
    """state.json is missing, unreadable or not a job state."""


def read_state(path):
    try:
        with open(path, encoding="utf-8") as f:
            state = json.load(f)
    except FileNotFoundError:
        raise StateError(f"no state.json at {path}")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        raise StateError(f"state.json unreadable at {path}: {e}")
    if not isinstance(state, dict) or not isinstance(state.get("workers", []), list) or not all(
            isinstance(w, dict) and isinstance(w.get("id"), str) for w in state.get("workers", [])):
        raise StateError(f"state.json at {path} is not a job state (an object whose workers each have an id)")
    return state


def load_state(state_dir, tries=5, pause=0.2):
    """Read DIR/state.json; a file caught mid-write is read again before it counts as an error."""
    path = os.path.join(state_dir, "state.json")
    for attempt in range(tries):
        try:
            return read_state(path)
        except StateError:
            if attempt == tries - 1:
                raise
            time.sleep(pause)


def running(state):
    workers = [w for w in state.get("workers", []) if w.get("status") == "running"]
    return sorted(workers, key=lambda w: w.get("started", ""))


def cmd_status(args):
    avail, total = memory_mb()
    per_agent = args.per_agent or PROFILES[args.profile]
    reserve = args.reserve or default_reserve(total)
    print(json.dumps({
        "avail_mb": avail, "total_mb": total, "reserve_mb": reserve,
        "per_agent_mb": per_agent, "slots": slots(avail, reserve, per_agent, args.max),
    }))


def cmd_watch(args):
    try:
        return watch(args)
    except StateError as e:
        print(json.dumps({"event": "error", "error": str(e)}))
        return 1


def watch(args):
    stop_dir = os.path.join(args.state, "stop")
    flagged_at = {}
    min_avail = None
    while True:
        state = load_state(args.state)
        os.makedirs(stop_dir, exist_ok=True)
        live = running(state)
        if not live:
            print(json.dumps({"event": "idle", "min_avail_mb": min_avail}))
            return 0
        avail, total = memory_mb()
        min_avail = avail if min_avail is None else min(min_avail, avail)
        reserve = state.get("reserve_mb") or default_reserve(total)
        per_agent = state.get("per_agent_mb") or PROFILES["light"]
        now = time.time()
        for w in live:
            if os.path.exists(os.path.join(stop_dir, w["id"])):
                flagged_at.setdefault(w["id"], now)
        if avail < reserve:
            overdue = [i for i, t in flagged_at.items()
                       if now - t > args.grace and any(w["id"] == i for w in live)]
            if overdue:
                print(json.dumps({"event": "hard-stop", "workers": overdue, "avail_mb": avail}))
                return 4
            unflagged = [w for w in live if w["id"] not in flagged_at]
            # workers already flagged will free their share once they checkpoint and exit
            need = math.ceil((reserve - avail) / per_agent) - (len(live) - len(unflagged))
            shed = list(reversed(unflagged))[:need]  # newest first: least work lost
            if shed:
                for w in shed:
                    open(os.path.join(stop_dir, w["id"]), "w").close()
                print(json.dumps({"event": "pressure", "stop": [w["id"] for w in shed],
                                  "avail_mb": avail, "reserve_mb": reserve,
                                  "min_avail_mb": min_avail}))
                return 3
        time.sleep(args.interval)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("status")
    s.add_argument("--profile", choices=PROFILES, default="light")
    s.add_argument("--per-agent", type=int)
    s.add_argument("--reserve", type=int)
    s.add_argument("--max", type=int, default=6)
    w = sub.add_parser("watch")
    w.add_argument("--state", required=True)
    w.add_argument("--interval", type=float, default=10)
    w.add_argument("--grace", type=float, default=180)
    args = p.parse_args()
    return cmd_status(args) if args.cmd == "status" else cmd_watch(args)


if __name__ == "__main__":
    sys.exit(main() or 0)
