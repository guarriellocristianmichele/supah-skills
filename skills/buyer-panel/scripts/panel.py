#!/usr/bin/env python3
"""Validate and aggregate a synthetic buyer panel kept in the panel ledger.

Usage:
  panel.py [--json] validate FILE...
  panel.py [--json] deal --buyers FILE --options ID,ID,... [--batch-size N] [--seed N] --out FILE
  panel.py [--json] reactions ROUND_DIR [--seed N] --out FILE
  panel.py [--json] aggregate ROUND_DIR [--buyers FILE] [--weights W5,W4,W3,W2,W1] [--out FILE]

validate   checks records against the schemas in RECORDS.md; the kind comes from the file name
           (buyers.jsonl, answers.jsonl or answers/*.jsonl, scores.jsonl, brief.json, plan.json, round.json).
deal       gives every buyer the options in its own random order and puts buyers in batches mixed across
           segments, for the interviews; writes one card line per buyer to --out.
reactions  writes what the judge may see: buyer id and free reaction only, in shuffled order.
aggregate  turns one round (round.json, answers, scores) into numbers: raw and discounted BUY share with the
           weighting scheme named, reasons with counts, buyer types, and the Van Westendorp price range with
           out-of-order answers dropped and counted. Buyers default to ROUND_DIR/../../buyers.jsonl.

Exit codes: 0 done; 1 a check failed (reserved for checks); 2 bad usage; 3 invalid records (nothing is
aggregated from them). Stdlib only.
"""
import argparse
import json
import os
import random
import sys

COMMANDS = {}


class UsageError(Exception):
    """Bad arguments: printed to stderr, exit 2."""


def command(name, help, show, arguments=()):
    """Register a subcommand. `arguments` are (flags, options) pairs for argparse; the function gets the parsed
    args and returns (result, exit code); `show` prints the result when --json is not given."""
    def wrap(fn):
        COMMANDS[name] = (fn, help, show, arguments)
        return fn
    return wrap


# ---------------------------------------------------------------- records

TEXT, NUMBER, ANY_TEXT = "text", "number", "any text"
OFFER, NOTHING = "offer", "nothing"              # reserved option ids: the idea, and "buy nothing"
PRICE_ANSWERS = ("too_cheap", "cheap", "expensive", "too_expensive")
INTENTS = (1, 2, 3, 4, 5)
SCHEMAS = {
    "buyers": {"id": TEXT, "name": TEXT, "segment": TEXT, "budget": NUMBER, "currency": TEXT, "habits": TEXT,
               "current_solution": TEXT, "last_spend": NUMBER, "objection": TEXT},
    "answers": {"buyer_id": TEXT, "round": TEXT, "reaction": TEXT, "choice": TEXT, "give_up": ANY_TEXT},
    "scores": {"buyer_id": TEXT, "round": TEXT, "reason": TEXT, "quote": TEXT},
}
KEY = {"buyers": "id", "answers": "buyer_id", "scores": "buyer_id"}
# single-object files
OBJECTS = {
    "brief": {"idea": TEXT, "audience": TEXT, "price": NUMBER, "currency": TEXT},
    "plan": {"currency": TEXT},
    "round": {"label": TEXT, "offer": TEXT, "price": NUMBER, "currency": TEXT, "model": TEXT},
}
INTERVIEWS = ("orchestrate", "inline")   # fresh contexts in batches, or one buyer at a time in this context


def kind_of(path):
    base = os.path.basename(path)
    if os.path.basename(os.path.dirname(path)) == "answers" and base.endswith(".jsonl"):
        return "answers"
    stem = base.split(".")[0]
    return stem if stem in SCHEMAS or stem in OBJECTS else None


def is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def is_count(v, least=1):
    return isinstance(v, int) and not isinstance(v, bool) and v >= least


def is_tag(v):
    """A reason tag: lowercase words joined by hyphens, so counts merge across buyers."""
    return isinstance(v, str) and bool(v) and all(part and part.isalnum() and part == part.lower()
                                                  for part in v.split("-"))


def field_errors(record, schema):
    errors = []
    for field, kind in schema.items():
        if field not in record:
            errors.append((field, "missing"))
        elif kind == TEXT and not (isinstance(record[field], str) and record[field].strip()):
            errors.append((field, "must be non-empty text"))
        elif kind == ANY_TEXT and not isinstance(record[field], str):
            errors.append((field, "must be text"))
        elif kind == NUMBER and not (is_number(record[field]) and record[field] >= 0):
            errors.append((field, "must be a number of 0 or more"))
    return errors


def answer_errors(rec):
    errors = option_errors(rec.get("options"))
    options = rec.get("options") if not errors else []
    if options and isinstance(rec.get("choice"), str) and rec["choice"] not in options:
        errors.append(("choice", "is not one of the options shown"))
    if rec.get("choice") == OFFER and isinstance(rec.get("give_up"), str) and not rec["give_up"].strip():
        errors.append(("give_up", "a BUY must say what the buyer gives up to pay"))
    price = rec.get("price")
    if not isinstance(price, dict):
        errors.append(("price", "must hold the four Van Westendorp answers"))
    else:
        for name in PRICE_ANSWERS:
            if not (is_number(price.get(name)) and price[name] >= 0):
                errors.append((f"price.{name}", "missing" if name not in price else "must be a number of 0 or more"))
    return errors


def score_errors(rec):
    errors = []
    intent = rec.get("intent")
    if not (isinstance(intent, int) and not isinstance(intent, bool) and intent in INTENTS):
        errors.append(("intent", "must be a whole number from 1 to 5 (the anchor statements)"))
    if "reason" in rec and isinstance(rec["reason"], str) and rec["reason"].strip() and not is_tag(rec["reason"]):
        errors.append(("reason", "must be a tag such as already-paid"))
    return errors


def option_errors(options, field="options"):
    if not (isinstance(options, list) and options and all(isinstance(o, str) and o for o in options)):
        return [(field, "must list option ids")]
    if len(set(options)) != len(options) or OFFER not in options or NOTHING not in options:
        return [(field, f"must be distinct and include {OFFER!r} and {NOTHING!r}")]
    return []


def brief_errors(rec):
    alts = rec.get("alternatives")
    if not (isinstance(alts, list) and alts):
        return [("alternatives", "must list the real alternatives with their prices")]
    errors = []
    for i, alt in enumerate(alts):
        if not isinstance(alt, dict):
            errors.append((f"alternatives[{i}]", "must be an object with name and price"))
            continue
        errors += [(f"alternatives[{i}].{f}", m) for f, m in field_errors(alt, {"name": TEXT, "price": NUMBER})]
        if alt.get("name") in (OFFER, NOTHING):
            errors.append((f"alternatives[{i}].name", f"{alt['name']!r} is a reserved option id"))
    return errors


def plan_errors(rec):
    errors = [] if is_count(rec.get("size")) else [("size", "must be a whole number of buyers")]
    segments = rec.get("segments")
    if not (isinstance(segments, list) and segments and all(isinstance(x, dict) for x in segments)):
        return errors + [("segments", "must list segments with name, share and budget")]
    names = [x.get("name") for x in segments]
    if len(set(names)) != len(names):
        errors.append(("segments", "segment names must be distinct"))
    for i, seg in enumerate(segments):
        errors += [(f"segments[{i}].{f}", m) for f, m in field_errors(seg, {"name": TEXT})]
        if not (is_number(seg.get("share")) and seg["share"] > 0):
            errors.append((f"segments[{i}].share", "must be a number above 0"))
        budget = seg.get("budget")
        if not (isinstance(budget, list) and len(budget) == 2 and all(is_number(b) and b >= 0 for b in budget)
                and budget[0] <= budget[1]):
            errors.append((f"segments[{i}].budget", "must be [low, high] with low <= high"))
    shares = [x["share"] for x in segments if is_number(x.get("share"))]
    if len(shares) == len(segments) and abs(sum(shares) - 1) > 0.01:
        errors.append(("segments.share", f"shares add up to {sum(shares):g}, not 1"))
    return errors


def round_errors(rec):
    errors = option_errors(rec.get("options"))
    if rec.get("interviews") not in INTERVIEWS:
        errors.append(("interviews", f"must be one of {', '.join(INTERVIEWS)}"))
    if not is_count(rec.get("batch_size")):
        errors.append(("batch_size", "must be a whole number of buyers per context (1 when inline)"))
    return errors


EXTRA = {"answers": answer_errors, "scores": score_errors, "brief": brief_errors, "plan": plan_errors,
         "round": round_errors}


def record_errors(kind, rec):
    errors = field_errors(rec, SCHEMAS.get(kind) or OBJECTS[kind])
    if kind in EXTRA:
        errors += EXTRA[kind](rec)
    return errors


def read_jsonl(path):
    """Yield (line number, record or None, parse error or None)."""
    with open(path, encoding="utf-8") as f:
        for n, raw in enumerate(f, 1):
            if not raw.strip():
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError as e:
                yield n, None, f"not JSON: {e.msg}"
                continue
            yield n, rec, None if isinstance(rec, dict) else "not a JSON object"


def validate_file(path):
    kind = kind_of(path)
    if kind is None:
        return {"file": path, "kind": None, "records": 0,
                "errors": [{"line": 0, "field": None, "problem": "unknown file name; see RECORDS.md"}]}
    if kind in OBJECTS:
        return validate_object(path, kind)
    errors, records, numbers, seen = [], [], [], set()
    for n, rec, problem in read_jsonl(path):
        if problem:
            errors.append({"line": n, "field": None, "problem": problem})
            continue
        records.append(rec)
        numbers.append(n)
        for field, msg in record_errors(kind, rec):
            errors.append({"line": n, "field": field, "problem": msg})
        key = rec.get(KEY[kind])
        if key in seen:
            errors.append({"line": n, "field": KEY[kind], "problem": f"duplicate {key}"})
        seen.add(key)
    return {"file": path, "kind": kind, "records": len(records), "errors": errors, "data": records,
            "lines": numbers}


def show_validate(results):
    for r in results:
        print(f"{r['file']}: {r['kind'] or '?'}, {r['records']} records, {len(r['errors'])} errors")
        for e in r["errors"]:
            print(f"  line {e['line']}: {e['field'] or '-'}: {e['problem']}")


def validate_object(path, kind):
    try:
        with open(path, encoding="utf-8") as f:
            rec = json.load(f)
    except json.JSONDecodeError as e:
        return {"file": path, "kind": kind, "records": 0, "data": None,
                "errors": [{"line": e.lineno, "field": None, "problem": f"not JSON: {e.msg}"}]}
    if not isinstance(rec, dict):
        return {"file": path, "kind": kind, "records": 0, "data": None,
                "errors": [{"line": 1, "field": None, "problem": "not a JSON object"}]}
    errors = [{"line": 0, "field": f, "problem": m} for f, m in record_errors(kind, rec)]
    return {"file": path, "kind": kind, "records": 1, "errors": errors, "data": rec}


def plan_fit_errors(buyers, numbers, plan):
    """Line-numbered errors for buyers outside the segment plan (unknown segment, budget out of range)."""
    ranges = {seg["name"]: seg["budget"] for seg in plan["segments"]}
    errors = []
    for n, rec in zip(numbers, buyers):
        seg = rec.get("segment")
        if isinstance(seg, str) and seg not in ranges:
            errors.append({"line": n, "field": "segment", "problem": f"{seg!r} is not in the plan"})
        elif seg in ranges and is_number(rec.get("budget")):
            low, high = ranges[seg]
            if not low <= rec["budget"] <= high:
                errors.append({"line": n, "field": "budget",
                               "problem": f"{rec['budget']:g} is outside the plan's {low:g} to {high:g}"})
    return errors


@command("validate", "check record files against their schemas", show_validate,
         [(("files",), {"nargs": "+", "metavar": "FILE"})])
def cmd_validate(args):
    results = [validate_file(p) for p in args.files]
    plans = {os.path.dirname(os.path.abspath(r["file"])): r for r in results if r["kind"] == "plan"}
    for r in results:
        if r["kind"] != "buyers" or r["errors"]:
            continue
        folder = os.path.dirname(os.path.abspath(r["file"]))
        plan = plans.get(folder)
        if plan is None and os.path.exists(os.path.join(folder, "plan.json")):
            plan = validate_file(os.path.join(folder, "plan.json"))
        if plan is not None and not plan["errors"]:
            r["errors"] = plan_fit_errors(r["data"], r["lines"], plan["data"])
            r["plan"] = plan["file"]
    for r in results:
        r.pop("data")
        r.pop("lines", None)
    return results, 3 if any(r["errors"] for r in results) else 0


# ---------------------------------------------------------------- interviews

def mixed_order(buyers):
    """One buyer from each segment in turn (segments in order of first appearance), so batches mix segments."""
    queues = {}
    for b in buyers:
        queues.setdefault(b["segment"], []).append(b)
    order = []
    while any(queues.values()):
        for q in queues.values():
            if q:
                order.append(q.pop(0))
    return order


def show_deal(result):
    if "errors" in result:
        return show_errors(result)
    print(f"{result['buyers']} cards in {result['batches']} batches of up to {result['batch_size']}, "
          f"seed {result['seed']}: {result['out']}")


@command("deal", "give each buyer the options in its own order, in batches mixed across segments", show_deal, [
    (("--buyers",), {"required": True, "metavar": "FILE"}),
    (("--options",), {"required": True, "metavar": "ID,ID,...",
                      "help": "option ids: offer, nothing and the alternatives' names"}),
    (("--batch-size",), {"type": int, "default": 5, "metavar": "N", "help": "buyers per interview context (5)"}),
    (("--seed",), {"type": int, "metavar": "N", "help": "random seed, recorded (default: a fresh one)"}),
    (("--out",), {"required": True, "metavar": "FILE", "help": "where to write one card line per buyer"}),
])
def cmd_deal(args):
    options = [o.strip() for o in args.options.split(",") if o.strip()]
    problems = option_errors(options)
    if problems:
        raise UsageError(f"--options {problems[0][1]}")
    if args.batch_size < 1:
        raise UsageError("--batch-size must be 1 or more")
    checked = validate_file(args.buyers)
    if checked["kind"] != "buyers" or checked["errors"]:
        return {"errors": [dict(e, file=args.buyers) for e in checked["errors"]]
                or [{"file": args.buyers, "line": 0, "field": None, "problem": "not a buyers.jsonl file"}]}, 3
    seed = args.seed if args.seed is not None else random.SystemRandom().randrange(10 ** 6)
    rng = random.Random(seed)
    cards = []
    for i, buyer in enumerate(mixed_order(checked["data"])):
        shown = options[:]
        rng.shuffle(shown)
        cards.append({"buyer_id": buyer["id"], "batch": i // args.batch_size + 1, "options": shown})
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.writelines(json.dumps(c, ensure_ascii=False) + "\n" for c in cards)
    return {"out": args.out, "buyers": len(cards), "batches": cards[-1]["batch"] if cards else 0,
            "batch_size": args.batch_size, "seed": seed}, 0


# ---------------------------------------------------------------- rounds

# Stated intent to likely purchase: the top-box scheme Jamieson and Bass (1989) compared, as described by
# Chandon, Morwitz and Reinartz (docs/research/2026-11-synthetic-panels.md, "Stated intent against actual purchase").
WEIGHTS = {"scheme": "top-box 75/25/10/5/2 (Jamieson and Bass 1989)",
           "by_intent": {"5": 0.75, "4": 0.25, "3": 0.1, "2": 0.05, "1": 0.02}}


def parse_weights(text):
    if text is None:
        return WEIGHTS
    try:
        values = [float(x) for x in text.split(",")]
    except ValueError:
        values = []
    if len(values) != 5 or not all(0 <= v <= 1 for v in values):
        raise UsageError("--weights takes five shares from 0 to 1, for intent 5 down to 1")
    return {"scheme": "custom " + "/".join(f"{v * 100:g}" for v in values),
            "by_intent": {str(5 - i): v for i, v in enumerate(values)}}


def normalise(text):
    return " ".join(text.lower().split())


def load_round(round_dir, buyers_path=None):
    """Read and cross-check a round. Returns (round, buyers by id, answers by id, scores by id, errors)."""
    buyers_path = buyers_path or os.path.join(round_dir, os.pardir, os.pardir, "buyers.jsonl")
    files = [os.path.join(round_dir, "round.json"), os.path.normpath(buyers_path)]
    answer_files = [os.path.join(round_dir, "answers.jsonl")] if os.path.exists(
        os.path.join(round_dir, "answers.jsonl")) else []
    batch_dir = os.path.join(round_dir, "answers")
    if os.path.isdir(batch_dir):
        answer_files += [os.path.join(batch_dir, f) for f in sorted(os.listdir(batch_dir)) if f.endswith(".jsonl")]
    files += answer_files
    if os.path.exists(os.path.join(round_dir, "scores.jsonl")):
        files.append(os.path.join(round_dir, "scores.jsonl"))
    errors = []
    for f in files[:2]:
        if not os.path.exists(f):
            errors.append({"file": f, "line": 0, "field": None, "problem": "missing"})
    if errors:
        return None, {}, {}, {}, errors
    results = [validate_file(f) for f in files]
    for r in results:
        errors += [dict(e, file=r["file"]) for e in r["errors"]]
    if errors:
        return None, {}, {}, {}, errors
    meta = results[0]["data"]
    buyers = {b["id"]: b for b in results[1]["data"]}
    answers, scores, where_scored = {}, {}, {}
    for r in results[2:]:
        into = answers if r["kind"] == "answers" else scores
        for n, rec in zip(r["lines"], r["data"]):
            where = {"file": r["file"], "line": n}
            bid = rec["buyer_id"]
            if bid not in buyers:
                errors.append(dict(where, field="buyer_id", problem=f"unknown buyer {bid}"))
            elif bid in into:
                errors.append(dict(where, field="buyer_id", problem=f"second record for {bid}"))
            if rec["round"] != meta["label"]:
                errors.append(dict(where, field="round", problem=f"{rec['round']!r} is not this round's label"))
            if r["kind"] == "answers" and sorted(rec["options"]) != sorted(meta["options"]):
                errors.append(dict(where, field="options", problem="not the round's options"))
            into[bid] = rec
            if r["kind"] == "scores":
                where_scored[bid] = where
    for bid, score in scores.items():
        answer = answers.get(bid)
        if answer and normalise(score["quote"]) not in normalise(answer["reaction"]):
            errors.append(dict(where_scored[bid], field="quote", problem=f"{bid}'s quote is not in their reaction"))
    return meta, buyers, answers, scores, errors


def share(part, whole):
    return round(part / whole, 4) if whole else None


def buy_share(rows, weights):
    buy = [r for r in rows if r["choice"] == OFFER]
    likely = sum(weights["by_intent"][str(r["intent"])] for r in buy)
    return {"buyers": len(rows), "buy": len(buy), "raw": share(len(buy), len(rows)),
            "discounted": share(likely, len(rows)), "weights": weights}


def reasons(rows, top=5):
    counts = {}
    for r in rows:
        counts[r["reason"]] = counts.get(r["reason"], 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [{"reason": k, "count": v} for k, v in ranked[:top]]


def buyer_types(rows, weights, top=3):
    """Segments ranked by discounted, then raw BUY share, then size: who to talk to first."""
    by_segment = {}
    for r in rows:
        by_segment.setdefault(r["segment"], []).append(r)
    types = [dict({"segment": seg}, **{k: v for k, v in buy_share(group, weights).items() if k != "weights"})
             for seg, group in by_segment.items()]
    types.sort(key=lambda t: (-t["discounted"], -t["raw"], -t["buyers"], t["segment"]))
    return types[:top]


def crossing(grid, f, g):
    """First price where f - g reaches 0 or changes sign, linear between grid points; None if never."""
    prev = None
    for p in grid:
        d = f(p) - g(p)
        if d == 0:
            return p
        if prev is not None and (prev[1] < 0) != (d < 0):
            p0, d0 = prev
            return round(p0 + (p - p0) * d0 / (d0 - d), 2)
        prev = (p, d)
    return None


def price_range(rows):
    """Van Westendorp price sensitivity meter (research note, "Pricing questions that work in a survey")."""
    valid, dropped = [], []
    for r in rows:
        a = r["price"]
        ordered = a["too_cheap"] < a["cheap"] < a["expensive"] < a["too_expensive"]
        (valid if ordered else dropped).append(r)
    out = {"valid": len(valid), "dropped": [r["buyer_id"] for r in dropped], "upper_bound": True,
           "marginal_cheapness": None, "marginal_expensiveness": None, "range": None, "optimal": None,
           "indifference": None}
    if not valid:
        return out
    answers = [r["price"] for r in valid]
    n = len(answers)
    grid = sorted({a[k] for a in answers for k in PRICE_ANSWERS})

    def at_least(key):
        return lambda p: sum(a[key] >= p for a in answers) / n

    def at_most(key):
        return lambda p: sum(a[key] <= p for a in answers) / n

    too_cheap, cheap = at_least("too_cheap"), at_least("cheap")
    expensive, too_expensive = at_most("expensive"), at_most("too_expensive")
    out["marginal_cheapness"] = crossing(grid, too_cheap, lambda p: 1 - cheap(p))
    out["marginal_expensiveness"] = crossing(grid, too_expensive, lambda p: 1 - expensive(p))
    out["optimal"] = crossing(grid, too_cheap, too_expensive)
    out["indifference"] = crossing(grid, cheap, expensive)
    if out["marginal_cheapness"] is not None and out["marginal_expensiveness"] is not None:
        out["range"] = [out["marginal_cheapness"], out["marginal_expensiveness"]]
    return out


def aggregate(meta, buyers, answers, scores, weights):
    rows = []
    for bid, buyer in buyers.items():
        if bid in answers and bid in scores:
            a, sc = answers[bid], scores[bid]
            rows.append({"buyer_id": bid, "name": buyer["name"], "segment": buyer["segment"],
                         "budget": buyer["budget"], "currency": buyer["currency"], "choice": a["choice"],
                         "decision": "BUY" if a["choice"] == OFFER else "PASS", "intent": sc["intent"],
                         "reason": sc["reason"], "quote": sc["quote"], "give_up": a["give_up"],
                         "price": a["price"], "options": a["options"]})
    return {
        "round": {k: meta[k] for k in ("label", "offer", "price", "currency", "model", "interviews", "batch_size")},
        "missing": {"answers": [b for b in buyers if b not in answers],
                    "scores": [b for b in answers if b not in scores]},
        "buy_share": buy_share(rows, weights),
        "pass_reasons": reasons([r for r in rows if r["decision"] == "PASS"]),
        "buy_reasons": reasons([r for r in rows if r["decision"] == "BUY"]),
        "buyer_types": buyer_types(rows, weights),
        "price": price_range(rows),
        "rows": rows,
    }


def show_reactions(result):
    if "errors" in result:
        return show_errors(result)
    print(f"{result['reactions']} reactions for the judge, seed {result['seed']}: {result['out']}")


@command("reactions", "write the judge's input: buyer id and reaction only, shuffled", show_reactions, [
    (("round_dir",), {"metavar": "ROUND_DIR"}),
    (("--buyers",), {"metavar": "FILE", "help": "buyers file (default ROUND_DIR/../../buyers.jsonl)"}),
    (("--seed",), {"type": int, "metavar": "N", "help": "random seed, recorded (default: a fresh one)"}),
    (("--out",), {"required": True, "metavar": "FILE"}),
])
def cmd_reactions(args):
    _, _, answers, _, errors = load_round(args.round_dir, args.buyers)
    if errors:
        return {"errors": errors}, 3
    seed = args.seed if args.seed is not None else random.SystemRandom().randrange(10 ** 6)
    shown = [{"buyer_id": bid, "reaction": a["reaction"]} for bid, a in answers.items()]
    random.Random(seed).shuffle(shown)
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.writelines(json.dumps(x, ensure_ascii=False) + "\n" for x in shown)
    return {"out": args.out, "reactions": len(shown), "seed": seed}, 0


def show_errors(result):
    for e in result["errors"]:
        print(f"{e['file']}:{e['line']}: {e['field'] or '-'}: {e['problem']}")


def pct(x):
    return "n/a" if x is None else f"{x * 100:.1f}%"


def cell(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def show_aggregate(result):
    """Markdown for the report: the summary, then the full buyer table."""
    if "errors" in result:
        return show_errors(result)
    s, p, rnd = result["buy_share"], result["price"], result["round"]
    cur = rnd["currency"]
    print(f"BUY {s['buy']} of {s['buyers']}: raw {pct(s['raw'])}, discounted {pct(s['discounted'])} "
          f"({s['weights']['scheme']})")
    for key, label in (("pass_reasons", "Top reasons to pass"), ("buy_reasons", "Top reasons to buy")):
        print(f"{label}: " + (", ".join(f"{r['reason']} {r['count']}" for r in result[key]) or "none"))
    print("Buyer types most likely to buy: " + ", ".join(
        f"{t['segment']} {t['buy']} of {t['buyers']} (discounted {pct(t['discounted'])})"
        for t in result["buyer_types"]))
    rng = f"{p['range'][0]:g} to {p['range'][1]:g} {cur}" if p["range"] else "no crossing"
    print(f"Price range (upper bound): {rng} from {p['valid']} answers; "
          f"dropped {len(p['dropped'])} out-of-order answers ({', '.join(p['dropped']) or 'none'})")
    for key in ("answers", "scores"):
        if result["missing"][key]:
            print(f"Missing {key}: {', '.join(result['missing'][key])}")
    print()
    print("| buyer | segment | budget | decision | intent | reason | in their words | gives up | "
          "too cheap / cheap / expensive / too expensive |")
    print("|---|---|---|---|---|---|---|---|---|")
    for r in result["rows"]:
        decision = r["decision"] if r["choice"] in (OFFER, NOTHING) else f"PASS ({r['choice']})"
        prices = " / ".join(f"{r['price'][k]:g}" for k in PRICE_ANSWERS)
        print(f"| {r['buyer_id']} {cell(r['name'])} | {cell(r['segment'])} | {r['budget']:g} {r['currency']} | "
              f"{decision} | {r['intent']} | {r['reason']} | \"{cell(r['quote'])}\" | {cell(r['give_up']) or '-'} | "
              f"{prices} |")


@command("aggregate", "turn one round into numbers", show_aggregate, [
    (("round_dir",), {"metavar": "ROUND_DIR"}),
    (("--buyers",), {"metavar": "FILE", "help": "buyers file (default ROUND_DIR/../../buyers.jsonl)"}),
    (("--weights",), {"metavar": "W5,W4,W3,W2,W1", "help": "intent weights, default 0.75,0.25,0.1,0.05,0.02"}),
    (("--out",), {"metavar": "FILE", "help": "also write the JSON result here"}),
])
def cmd_aggregate(args):
    weights = parse_weights(args.weights)
    meta, buyers, answers, scores, errors = load_round(args.round_dir, args.buyers)
    if errors:
        return {"errors": errors}, 3
    result = aggregate(meta, buyers, answers, scores, weights)
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as f:
            json.dump(result, f, ensure_ascii=False, indent=1)
            f.write("\n")
    return result, 0


# ---------------------------------------------------------------- main

def parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--json", action="store_true", help="print JSON instead of a short table")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, (_, help, _, arguments) in COMMANDS.items():
        cp = sub.add_parser(name, help=help)
        for flags, options in arguments:
            cp.add_argument(*flags, **options)
    return p


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    p = parser()
    args = p.parse_args(argv)
    fn, _, show, _ = COMMANDS[args.cmd]
    try:
        result, code = fn(args)
    except UsageError as e:
        p.error(str(e))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
    else:
        show(result)
    return code


if __name__ == "__main__":
    sys.exit(main())
