#!/usr/bin/env python3
"""Blocker graph for the orchestrate skill. Stdlib only; reads, never writes.

  graph.py frontier --state DIR
      Read DIR/units.md (| unit | status | blocked-by | files |) and print JSON:
      frontier  pending units whose blockers are all done, in table order
      waiting   pending units with the blockers still open
      blocked   pending units that can never start, with the failed unit at the root
      implied   blockers added because two units edit the same file
      Exit 0. Exit 2 with {"duplicate": [...]}, {"unknown": ...}, {"cycle": [...]} or {"error": ...}
      (no units.md) when no job can run.

  Units are rows in table order. blocked-by lists the unit ids that must be done
  first; a failed or blocked blocker blocks its dependents. Units sharing a path in
  files run one after the other, the earlier row first unless a blocker chain already
  orders them; that implied order only waits, so a failed unit releases the units it
  only overlaps. Paths are compared after normalising (`./a`, `a`, `.\\a`). Status:
  pending (also an empty cell), assigned:<worker>, done, failed:<reason>,
  blocked:<unit>, in any case. Tables without blocked-by or files columns are independent units.
"""
import argparse
import json
import os
import posixpath
import sys


def split(cell):
    return [x.strip() for x in cell.split(",") if x.strip() and x.strip().lower() != "none"]


def path_key(path):
    """One spelling per file: `src\\a.py`, `./src/a.py` and `src/a.py` are the same file."""
    return posixpath.normpath(path.replace("\\", "/"))


def status_of(cell):
    """An empty cell is pending; the keyword before `:` is matched in any case, the reason kept."""
    keyword, sep, reason = cell.strip().partition(":")
    return keyword.lower() + sep + reason if keyword else "pending"


def read_units(path):
    """Return [{unit, status, blocked_by, files}] in table order."""
    rows, columns = [], None
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if columns is None:
                columns = [c.lower() for c in cells]
                continue
            if all(set(c) <= set("-: ") for c in cells):
                continue
            row = dict(zip(columns, cells))
            rows.append({"unit": row.get("unit", ""), "status": status_of(row.get("status", "")),
                         "blocked_by": split(row.get("blocked-by", "")),
                         "files": [path_key(p) for p in split(row.get("files", ""))], "implied": []})
    return rows


def invalid(units):
    """Return {"duplicate": [...]}, {"unknown": {...}} or {"cycle": [...]} for a graph no job can run, else None."""
    ids = [u["unit"] for u in units]
    duplicate = sorted({i for i in ids if ids.count(i) > 1})
    if duplicate:
        return {"duplicate": duplicate}
    by_id = {u["unit"]: u for u in units}
    unknown = {u["unit"]: [b for b in u["blocked_by"] if b not in by_id] for u in units}
    unknown = {k: v for k, v in unknown.items() if v}
    if unknown:
        return {"unknown": unknown}
    done = set()

    def walk(unit, path):
        if unit in path:
            return path[path.index(unit):] + [unit]
        if unit in done:
            return None
        for b in by_id[unit]["blocked_by"]:
            cycle = walk(b, path + [unit])
            if cycle:
                return cycle
        done.add(unit)
        return None

    for u in units:
        cycle = walk(u["unit"], [])
        if cycle:
            return {"cycle": cycle}
    return None


def imply(units):
    """Order every pair of units that share a file and no blocker chain orders yet:
    the earlier one in table order goes first. Return {unit: [implied blockers]}."""
    by_id = {u["unit"]: u for u in units}

    def after(a, b):
        """True when a is transitively blocked by b, through declared or implied blockers."""
        seen, todo = set(), [a]
        while todo:
            unit = todo.pop()
            for x in by_id[unit]["blocked_by"] + by_id[unit]["implied"]:
                if x == b:
                    return True
                if x not in seen:
                    seen.add(x)
                    todo.append(x)
        return False

    for j, later in enumerate(units):
        for earlier in reversed(units[:j]):  # nearest first, so a chain needs no redundant edges
            if set(earlier["files"]) & set(later["files"]) and not (
                    after(later["unit"], earlier["unit"]) or after(earlier["unit"], later["unit"])):
                later["implied"].append(earlier["unit"])
    return {u["unit"]: u["implied"] for u in units if u["implied"]}


def frontier(units):
    """Return (frontier, waiting, blocked).

    frontier: pending units whose blockers are all done; waiting: pending units with
    their open blockers; blocked: pending units that can never start, with the failed
    unit at the root of the chain."""
    by_id = {u["unit"]: u for u in units}
    roots = {}

    def root(unit):
        if unit not in roots:
            u = by_id.get(unit)
            status = u["status"] if u else "pending"
            if status.startswith("failed"):
                roots[unit] = unit
            elif status.startswith("blocked:"):
                roots[unit] = status.split(":", 1)[1].strip()
            else:
                roots[unit] = next((r for r in map(root, u["blocked_by"] if u else []) if r), None)
        return roots[unit]

    ready, waiting, blocked = [], {}, {}
    for u in units:
        if u["status"] != "pending":
            continue
        if root(u["unit"]):
            blocked[u["unit"]] = root(u["unit"])
            continue
        # an implied blocker waits only while it is running or can still run
        open_ = [b for b in u["blocked_by"] if by_id[b]["status"] != "done"] + [
            b for b in u["implied"] if by_id[b]["status"].startswith("assigned")
            or by_id[b]["status"] == "pending" and not root(b)]
        if open_:
            waiting[u["unit"]] = open_
        else:
            ready.append(u["unit"])
    return ready, waiting, blocked


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("frontier")
    f.add_argument("--state", required=True)
    args = p.parse_args()
    path = os.path.join(args.state, "units.md")
    if not os.path.exists(path):
        print(json.dumps({"error": "no units.md in %s" % args.state}))
        return 2
    units = read_units(path)
    error = invalid(units)
    if error:
        print(json.dumps(error))
        return 2
    implied = imply(units)
    ready, waiting, blocked = frontier(units)
    print(json.dumps({"frontier": ready, "waiting": waiting, "blocked": blocked, "implied": implied}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
