#!/usr/bin/env python3
"""Validate and aggregate a synthetic buyer panel kept in the panel ledger.

Usage:
  panel.py [--json] validate FILE...
  panel.py [--json] deal --buyers FILE --options ID,ID,... [--batch-size N] [--seed N] --out FILE
  panel.py [--json] reactions ROUND_DIR [--seed N] --out FILE
  panel.py [--json] aggregate ROUND_DIR [--buyers FILE] [--weights W5,W4,W3,W2,W1] [--out FILE]
  panel.py [--json] diff ROUND_A ROUND_B [--buyers FILE] [--weights W5,W4,W3,W2,W1] [--out FILE]
  panel.py [--json] page ROUND_DIR [--buyers FILE] [--weights W5,W4,W3,W2,W1] [--data FILE] [--out FILE]

validate   checks records against the schemas in RECORDS.md; the kind comes from the file name
           (buyers.jsonl, answers.jsonl or answers/*.jsonl, scores.jsonl, brief.json, plan.json, round.json).
deal       gives every buyer the options in its own random order and puts buyers in batches mixed across
           segments, for the interviews; writes one card line per buyer to --out.
reactions  writes what the judge may see: buyer id and free reaction only, in shuffled order.
aggregate  turns one round (round.json, answers, scores) into numbers: raw and discounted BUY share with the
           weighting scheme named, reasons with counts, buyer types, and the Van Westendorp price range with
           out-of-order answers dropped and counted. Buyers default to ROUND_DIR/../../buyers.jsonl.
diff       compares two rounds of the same panel over the buyers answered and scored in both: PASS to BUY
           and back, every change of option (between competitors too), choices per option, BUY share,
           intent, new and gone top reasons, and the card price and price range moved.
page       writes the page data for a round (default ROUND_DIR/page.json) and a self-contained HTML page
           from it (default ROUND_DIR/page.html): the simulated-panel line, the summary, any checks found in
           ROUND_DIR/summary.json, the price curves as inline SVG and the buyer table with filters.

Exit codes: 0 done; 1 a check failed (reserved for checks); 2 bad usage; 3 invalid records (nothing is
aggregated from them). Stdlib only.
"""
import argparse
import html
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


# --- diff ---

def load_rows(round_dir, buyers_path, weights):
    """One round's meta and rows by buyer id, or raise the round's record errors."""
    meta, buyers, answers, scores, errors = load_round(round_dir, buyers_path)
    if errors:
        return None, None, errors
    result = aggregate(meta, buyers, answers, scores, weights)
    return meta, {r["buyer_id"]: r for r in result["rows"]}, []


def points(x):
    return "n/a" if x is None else f"{x * 100:+.1f} points"


def ids(xs):
    return ", ".join(xs) or "none"


def decision_label(side):
    return side["decision"] if side["choice"] in (OFFER, NOTHING) else f"PASS ({side['choice']})"


def show_diff(result):
    """Markdown for the report: what moved between the rounds, then every buyer compared."""
    if "errors" in result:
        return show_errors(result)
    a, b = result["before"]["label"], result["after"]["label"]
    s, i, p = result["buy_share"], result["intent"], result["price"]
    print(f"{a} -> {b}: {result['buyers']['both']} buyers in both rounds")
    for label, key in ((a, "only_before"), (b, "only_after")):
        if result["buyers"][key]:
            print(f"Only in {label} (not compared): {ids(result['buyers'][key])}")
    print(f"BUY {s['before']['buy']} of {s['before']['buyers']} -> {s['after']['buy']} of {s['after']['buyers']}: "
          f"raw {pct(s['before']['raw'])} -> {pct(s['after']['raw'])} ({points(s['raw_change'])}), "
          f"discounted {pct(s['before']['discounted'])} -> {pct(s['after']['discounted'])} "
          f"({points(s['discounted_change'])}), weights {s['scheme']}")
    print(f"PASS to BUY: {ids(result['flips']['pass_to_buy'])}. BUY to PASS: {ids(result['flips']['buy_to_pass'])}.")
    print("Switches: " + (", ".join(f"{x['buyer_id']} {x['from']} -> {x['to']}" for x in result["switches"])
                          or "none"))
    print("Choices: " + ", ".join(f"{c['option']} {c['before']} -> {c['after']}" for c in result["choices"]))
    if i["before"] is not None:
        print(f"Mean intent {i['before']:.2f} -> {i['after']:.2f} ({i['change']:+.2f}): up {ids(i['up'])}; "
              f"down {ids(i['down'])}; {i['same']} the same")
    for key, label in (("pass_reasons", "Top reasons to pass"), ("buy_reasons", "Top reasons to buy")):
        r = result[key]
        listed = [", ".join(f"{x['reason']} {x['count']}" for x in r[side]) or "none" for side in ("before", "after")]
        print(f"{label}: {listed[0]} -> {listed[1]} (new: {ids(r['new'])}; gone: {ids(r['gone'])})")
    card = p["card"]
    ranges = [f"{x['range'][0]:g} to {x['range'][1]:g}" if x["range"] else "no crossing"
              for x in (p["before"], p["after"])]
    print(f"Card price {card['before']:g} -> {card['after']:g} {card['currency']}; "
          f"price range (upper bound) {ranges[0]} -> {ranges[1]} {card['currency']}")
    print()
    print(f"| buyer | segment | change | {a} | {b} | intent | reason | in their words ({b}) |")
    print("|---|---|---|---|---|---|---|---|")
    names = {"pass-to-buy": "PASS to BUY", "buy-to-pass": "BUY to PASS", "switch": "switch", "same": "-"}
    for r in result["rows"]:
        x, y = r["before"], r["after"]
        reason = x["reason"] if x["reason"] == y["reason"] else f"{x['reason']} -> {y['reason']}"
        print(f"| {r['buyer_id']} {cell(r['name'])} | {cell(r['segment'])} | {names[r['change']]} | "
              f"{decision_label(x)} | {decision_label(y)} | {x['intent']} -> {y['intent']} | {reason} | "
              f"\"{cell(y['quote'])}\" |")


@command("diff", "compare two rounds of the same buyers, buyer by buyer", show_diff, [
    (("before",), {"metavar": "ROUND_A"}),
    (("after",), {"metavar": "ROUND_B"}),
    (("--buyers",), {"metavar": "FILE", "help": "buyers file for both (default ROUND_A/../../buyers.jsonl)"}),
    (("--weights",), {"metavar": "W5,W4,W3,W2,W1", "help": "intent weights, default 0.75,0.25,0.1,0.05,0.02"}),
    (("--out",), {"metavar": "FILE", "help": "also write the JSON result here"}),
])
def cmd_diff(args):
    result, code = diff_rounds(args)
    if args.out and code == 0:
        with open(args.out, "w", encoding="utf-8", newline="\n") as f:
            json.dump(result, f, ensure_ascii=False, indent=1)
            f.write("\n")
    return result, code


def diff_rounds(args):
    weights = parse_weights(args.weights)
    if args.buyers is None:
        panels = {os.path.realpath(os.path.join(d, os.pardir, os.pardir)) for d in (args.before, args.after)}
        if len(panels) > 1:
            raise UsageError("the two rounds belong to different panels; diff compares rounds of the same buyers")
    meta_a, before, errors = load_rows(args.before, args.buyers, weights)
    meta_b, after, more = load_rows(args.after, args.buyers, weights)
    if errors or more:
        return {"errors": errors + more}, 3
    both = [bid for bid in before if bid in after]
    flips = {"pass_to_buy": [b for b in both if before[b]["decision"] == "PASS" and after[b]["decision"] == "BUY"],
             "buy_to_pass": [b for b in both if before[b]["decision"] == "BUY" and after[b]["decision"] == "PASS"]}
    switches = [{"buyer_id": b, "from": before[b]["choice"], "to": after[b]["choice"]}
                for b in both if before[b]["choice"] != after[b]["choice"]]
    options = meta_a["options"] + [o for o in meta_b["options"] if o not in meta_a["options"]]
    choices = [{"option": o, "before": sum(before[b]["choice"] == o for b in both),
                "after": sum(after[b]["choice"] == o for b in both)} for o in options]
    rows_a, rows_b = [before[b] for b in both], [after[b] for b in both]
    keep = ("label", "offer", "price", "currency", "model", "interviews", "batch_size")
    return {"before": {k: meta_a[k] for k in keep}, "after": {k: meta_b[k] for k in keep},
            "buyers": {"both": len(both), "only_before": [b for b in before if b not in after],
                       "only_after": [b for b in after if b not in before]},
            "flips": flips, "switches": switches, "choices": choices,
            "buy_share": share_shift(rows_a, rows_b, weights), "intent": intent_shift(both, before, after),
            "pass_reasons": reason_shift(rows_a, rows_b, "PASS"), "buy_reasons": reason_shift(rows_a, rows_b, "BUY"),
            "price": price_shift(meta_a, meta_b, rows_a, rows_b),
            "rows": [buyer_change(before[b], after[b]) for b in both]}, 0


def buyer_change(a, b):
    if a["decision"] != b["decision"]:
        kind = "pass-to-buy" if b["decision"] == "BUY" else "buy-to-pass"
    else:
        kind = "switch" if a["choice"] != b["choice"] else "same"
    side = ("choice", "decision", "intent", "reason", "quote", "give_up", "price")
    return {"buyer_id": a["buyer_id"], "name": a["name"], "segment": a["segment"], "change": kind,
            "before": {k: a[k] for k in side}, "after": {k: b[k] for k in side}}


def reason_shift(rows_a, rows_b, decision):
    """Top reasons in both rounds; `new` are top reasons after that were not top before, `gone` the reverse."""
    a = reasons([r for r in rows_a if r["decision"] == decision])
    b = reasons([r for r in rows_b if r["decision"] == decision])
    tags_a, tags_b = [x["reason"] for x in a], [x["reason"] for x in b]
    return {"before": a, "after": b, "new": [t for t in tags_b if t not in tags_a],
            "gone": [t for t in tags_a if t not in tags_b]}


def change(a, b):
    return None if a is None or b is None else round(b - a, 2)


def price_shift(meta_a, meta_b, rows_a, rows_b):
    a, b = price_range(rows_a), price_range(rows_b)
    return {"card": {"before": meta_a["price"], "after": meta_b["price"], "change": change(meta_a["price"],
                                                                                         meta_b["price"]),
                     "currency": meta_b["currency"]},
            "before": a, "after": b,
            "range_change": [change(a["range"][0], b["range"][0]), change(a["range"][1], b["range"][1])]
            if a["range"] and b["range"] else None,
            "optimal_change": change(a["optimal"], b["optimal"]),
            "indifference_change": change(a["indifference"], b["indifference"])}


def share_shift(rows_a, rows_b, weights):
    """BUY share in both rounds over the same buyers; changes from the counts, not the rounded shares."""
    def likely(rows):
        return sum(weights["by_intent"][str(r["intent"])] for r in rows if r["choice"] == OFFER)

    n = len(rows_a)
    a, b = buy_share(rows_a, weights), buy_share(rows_b, weights)
    for s in (a, b):
        del s["weights"]
    return {"before": a, "after": b, "raw_change": share(b["buy"] - a["buy"], n),
            "discounted_change": share(likely(rows_b) - likely(rows_a), n), "scheme": weights["scheme"]}


def intent_shift(both, before, after):
    n = len(both)
    total_a, total_b = sum(before[b]["intent"] for b in both), sum(after[b]["intent"] for b in both)
    return {"before": share(total_a, n), "after": share(total_b, n), "change": share(total_b - total_a, n),
            "up": [b for b in both if after[b]["intent"] > before[b]["intent"]],
            "down": [b for b in both if after[b]["intent"] < before[b]["intent"]],
            "same": sum(after[b]["intent"] == before[b]["intent"] for b in both)}


# --- page ---

def simulated_line(buyers, model):
    """The report's first line (SKILL.md, rule 1), for the page too."""
    return (f"Simulated panel: {buyers} synthetic buyers written by {model}, not real people. "
            "Every number below is a hypothesis to test on people.")


def price_curves(rows):
    """The four Van Westendorp curves at every price named, from the answers in order (as price_range)."""
    answers = [r["price"] for r in rows
               if r["price"]["too_cheap"] < r["price"]["cheap"] < r["price"]["expensive"] < r["price"]["too_expensive"]]
    n = len(answers)
    grid = sorted({a[k] for a in answers for k in PRICE_ANSWERS})
    points = [{"price": p,
               "too_cheap": share(sum(a["too_cheap"] >= p for a in answers), n),
               "cheap": share(sum(a["cheap"] >= p for a in answers), n),
               "expensive": share(sum(a["expensive"] <= p for a in answers), n),
               "too_expensive": share(sum(a["too_expensive"] <= p for a in answers), n)} for p in grid]
    return {"answers": n, "points": points}


def read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def page_data(round_dir, meta, buyers, answers, scores, weights):
    summary = aggregate(meta, buyers, answers, scores, weights)
    rows = summary.pop("rows")
    # Checks may come from aggregate itself or from a summary.json written by a later step; both are optional.
    checks = summary.pop("checks", None)
    if checks is None:
        checks = (read_json(os.path.join(round_dir, "summary.json")) or {}).get("checks")
    brief = read_json(os.path.join(round_dir, os.pardir, os.pardir, "brief.json")) or {}
    segments = []
    for r in rows:
        if r["segment"] not in segments:
            segments.append(r["segment"])
    return {
        "simulated": simulated_line(len(buyers), meta["model"]),
        "idea": brief.get("idea") if isinstance(brief.get("idea"), str) else meta["offer"],
        "round": summary.pop("round"),
        "summary": summary,
        "checks": checks,
        "filters": {"segment": segments,
                    "decision": [d for d in ("BUY", "PASS") if any(r["decision"] == d for r in rows)],
                    "reason": sorted({r["reason"] for r in rows})},
        "chart": price_curves(rows),
        "rows": rows,
    }


PAGE_CSS = """
:root {
  --bg: #f3f2ef; --surface: #fbfaf8; --text: #23221f; --muted: #57554f; --line: #d3d0c9;
  --buy: #2d6a39; --pass: #8b3a28; --note-bg: #fbf1d9; --note-line: #9a7414;
  --too-cheap: #1d6b87; --cheap: #4f8f33; --expensive: #a8661a; --too-expensive: #a23a3a; --band: #e3e9df;
  --radius: 6px; --gap: 1rem;
  color-scheme: light dark;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #1a1b1d; --surface: #222326; --text: #e9e7e2; --muted: #aeaba4; --line: #3b3c40;
    --buy: #86c78f; --pass: #e79a86; --note-bg: #3a3220; --note-line: #d9b35a;
    --too-cheap: #6cc0dd; --cheap: #9bd27f; --expensive: #e3a65c; --too-expensive: #ec8b8b; --band: #2c3a2c;
  }
}
:root[data-theme="dark"] {
  --bg: #1a1b1d; --surface: #222326; --text: #e9e7e2; --muted: #aeaba4; --line: #3b3c40;
  --buy: #86c78f; --pass: #e79a86; --note-bg: #3a3220; --note-line: #d9b35a;
  --too-cheap: #6cc0dd; --cheap: #9bd27f; --expensive: #e3a65c; --too-expensive: #ec8b8b; --band: #2c3a2c;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text);
  font: 1rem/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
main { max-width: 72rem; margin: 0 auto; padding: 1.5rem 1rem 3rem; }
h1 { font-size: 1.6rem; line-height: 1.25; margin: 1.25rem 0 0.25rem; }
h2 { font-size: 1.2rem; margin: 2rem 0 0.75rem; }
p { margin: 0 0 0.75rem; }
.simulated { background: var(--note-bg); border: 2px solid var(--note-line); border-radius: var(--radius);
  padding: 0.75rem 1rem; font-weight: 600; font-size: 1.05rem; margin: 0; }
.meta, .scheme, .count { color: var(--muted); }
.summary { display: grid; grid-template-columns: max-content 1fr; gap: 0.4rem 1.25rem; margin: 0; }
.summary dt { font-weight: 600; }
.summary dd { margin: 0; }
.checks { padding-left: 1.25rem; }
.failed { color: var(--pass); font-weight: 600; }
.passed { color: var(--buy); font-weight: 600; }
figure { margin: 0; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius);
  padding: var(--gap); }
svg { display: block; width: 100%; max-width: 36rem; height: auto; }
svg text { fill: var(--muted); font-size: 14px; }
.axis { stroke: var(--line); stroke-width: 1; }
.band { fill: var(--band); }
.curve { fill: none; stroke-width: 2.5; }
.too-cheap { stroke: var(--too-cheap); } .cheap { stroke: var(--cheap); }
.expensive { stroke: var(--expensive); } .too-expensive { stroke: var(--too-expensive); }
.legend { display: flex; flex-wrap: wrap; gap: 0.5rem 1.25rem; padding: 0; margin: 0.75rem 0 0; list-style: none; }
.legend li::before { content: ""; display: inline-block; width: 1.25rem; height: 0; margin-right: 0.4rem;
  vertical-align: middle; border-top: 3px solid currentColor; }
.legend .too-cheap { color: var(--too-cheap); } .legend .cheap { color: var(--cheap); }
.legend .expensive { color: var(--expensive); } .legend .too-expensive { color: var(--too-expensive); }
.legend span { color: var(--text); }
figcaption { margin-top: 0.75rem; }
form { display: flex; flex-wrap: wrap; gap: 0.75rem 1.25rem; align-items: end; margin: 0 0 1rem; }
label { display: flex; flex-direction: column; gap: 0.2rem; font-weight: 600; }
select { font: inherit; color: var(--text); background: var(--surface); border: 1px solid var(--line);
  border-radius: var(--radius); padding: 0.35rem 0.5rem; min-width: 9rem; }
table { width: 100%; border-collapse: collapse; background: var(--surface); }
th, td { text-align: left; vertical-align: top; padding: 0.5rem 0.6rem; border-bottom: 1px solid var(--line); }
th { font-weight: 600; }
td.num { white-space: nowrap; }
.BUY { color: var(--buy); font-weight: 600; }
.PASS { color: var(--pass); font-weight: 600; }
@media (max-width: 48rem) {
  .summary { grid-template-columns: 1fr; }
  .summary dd { margin-bottom: 0.5rem; }
  thead { display: none; }
  table, tbody, tr, td { display: block; }
  tr { border: 1px solid var(--line); border-radius: var(--radius); margin-bottom: 0.75rem; padding: 0.25rem 0; }
  td { border: 0; padding: 0.3rem 0.75rem; display: grid; grid-template-columns: 7rem 1fr; gap: 0.75rem; }
  td::before { content: attr(data-label); color: var(--muted); }
}
"""

PAGE_JS = """
(function () {
  var form = document.getElementById("filters");
  var rows = Array.prototype.slice.call(document.querySelectorAll("tbody tr"));
  var count = document.getElementById("count");
  function apply() {
    var shown = 0;
    rows.forEach(function (row) {
      var keep = ["segment", "decision", "reason"].every(function (name) {
        var value = document.getElementById("filter-" + name).value;
        return !value || row.getAttribute("data-" + name) === value;
      });
      row.hidden = !keep;
      if (keep) { shown += 1; }
    });
    count.textContent = "Showing " + shown + " of " + rows.length + " buyers.";
  }
  form.hidden = false;
  form.addEventListener("change", apply);
  apply();
})();
"""

CURVES = (("too_cheap", "too-cheap", "Too cheap at this price"), ("cheap", "cheap", "A bargain at this price"),
          ("expensive", "expensive", "Expensive at this price"),
          ("too_expensive", "too-expensive", "Too expensive at this price"))


def esc(value):
    return html.escape(str(value), quote=True)


def money(value, currency):
    return f"{value:g} {esc(currency)}"


def price_svg(chart, price, currency):
    """Inline SVG of the four Van Westendorp curves, with the acceptable range shaded."""
    points = chart["points"]
    if len(points) < 2:
        return "<p>Not enough answers in order to draw the price curves.</p>"
    w, h, left, right, top, bottom = 420, 250, 46, 12, 10, 40
    low, high = points[0]["price"], points[-1]["price"]

    def x(p):
        return round(left + (p - low) / (high - low) * (w - left - right), 1)

    def y(s):
        return round(top + (1 - s) * (h - top - bottom), 1)

    parts = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-labelledby="chart-title">',
             f'<title id="chart-title">Van Westendorp price curves, {chart["answers"]} answers in order</title>']
    if price["range"]:
        a, b = price["range"]
        parts.append(f'<rect class="band" x="{x(a)}" y="{top}" width="{round(x(b) - x(a), 1)}" '
                     f'height="{h - top - bottom}"/>')
    for s in (0, 0.5, 1):
        parts.append(f'<line class="axis" x1="{left}" y1="{y(s)}" x2="{w - right}" y2="{y(s)}"/>')
        parts.append(f'<text x="{left - 8}" y="{y(s) + 5}" text-anchor="end">{round(s * 100)}%</text>')
    ticks = sorted({low, high, *(price["range"] or [])})
    for t in ticks:
        parts.append(f'<text x="{x(t)}" y="{h - bottom + 22}" text-anchor="middle">{t:g}</text>')
    parts.append(f'<text x="{w - right}" y="{h - 2}" text-anchor="end">{esc(currency)}</text>')
    for key, css, _ in CURVES:
        coords = " ".join(f"{x(pt['price'])},{y(pt[key])}" for pt in points)
        parts.append(f'<polyline class="curve {css}" points="{coords}"/>')
    parts.append("</svg>")
    return "\n".join(parts)


def check_items(checks):
    """(name, passed or None, detail) from whatever shape the checks take: a list of objects or a mapping."""
    if isinstance(checks, dict):
        entries = [(k, v) for k, v in checks.items()]
    elif isinstance(checks, list):
        entries = [((c.get("name") or c.get("check") or c.get("id") or f"check {i + 1}") if isinstance(c, dict)
                    else f"check {i + 1}", c) for i, c in enumerate(checks)]
    else:
        return []
    items = []
    for name, value in entries:
        passed = None
        if isinstance(value, bool):
            passed, detail = value, ""
        elif isinstance(value, dict):
            if isinstance(value.get("passed"), bool):
                passed = value["passed"]
            elif isinstance(value.get("ok"), bool):
                passed = value["ok"]
            elif isinstance(value.get("failed"), bool):
                passed = not value["failed"]
            elif value.get("status") in ("pass", "passed", "ok", "fail", "failed"):
                passed = value["status"] in ("pass", "passed", "ok")
            skip = {"name", "check", "id", "passed", "ok", "failed", "status"}
            detail = ", ".join(f"{k} {json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v}"
                               for k, v in value.items() if k not in skip)
        else:
            detail = str(value)
        items.append((str(name), passed, detail))
    return items


def checks_html(checks):
    items = check_items(checks)
    if not items:
        return ""
    out = ['<section aria-labelledby="checks"><h2 id="checks">Checks</h2><ul class="checks">']
    for name, passed, detail in items:
        status = ("" if passed is None else
                  ' <span class="passed">passed</span>' if passed else ' <span class="failed">failed</span>')
        out.append(f"<li><strong>{esc(name)}</strong>{status}{': ' + esc(detail) if detail else ''}</li>")
    out.append("</ul></section>")
    return "\n".join(out)


def page_html(data):
    rnd, s = data["round"], data["summary"]
    share_, price, cur = s["buy_share"], s["price"], rnd["currency"]

    def reason_list(items):
        return ", ".join(f"{esc(r['reason'])} ({r['count']})" for r in items) or "none"

    if price["range"]:
        span = f"{money(price['range'][0], cur)} to {money(price['range'][1], cur)}"
        if price["optimal"] is not None and price["indifference"] is not None:
            span += (f"; optimal point {money(price['optimal'], cur)}, "
                     f"indifference point {money(price['indifference'], cur)}")
    else:
        span = "no crossing in the answers"
    dropped = ", ".join(esc(b) for b in price["dropped"]) or "none"
    summary = [
        ("BUY share", f"{share_['buy']} of {share_['buyers']}: raw {pct(share_['raw'])}, "
                      f"discounted {pct(share_['discounted'])} "
                      f"<span class=\"scheme\">({esc(share_['weights']['scheme'])})</span>"),
        ("Top reasons to pass", reason_list(s["pass_reasons"])),
        ("Top reasons to buy", reason_list(s["buy_reasons"])),
        ("Buyer types most likely to buy", ", ".join(
            f"{esc(t['segment'])} {t['buy']} of {t['buyers']} (discounted {pct(t['discounted'])})"
            for t in s["buyer_types"]) or "none"),
        ("Price range, an upper bound", f"{span}; from {price['valid']} answers in order, "
                                        f"{len(price['dropped'])} out-of-order answers dropped ({dropped})"),
    ]
    for key in ("answers", "scores"):
        if s["missing"][key]:
            summary.append((f"Missing {key}", ", ".join(esc(b) for b in s["missing"][key])))
    how = (f"orchestrate, in batches of {rnd['batch_size']} buyers in fresh contexts" if rnd["interviews"] == "orchestrate"
           else "inline, one buyer at a time in one context, so independence was partial")

    def select(name, label, values):
        opts = "".join(f'<option value="{esc(v)}">{esc(v)}</option>' for v in values)
        return (f'<label for="filter-{name}">{label}<select id="filter-{name}">'
                f'<option value="">All</option>{opts}</select></label>')

    rows = []
    for r in data["rows"]:
        decision = r["decision"] if r["choice"] in (OFFER, NOTHING) else f"PASS ({r['choice']})"
        prices = " / ".join(f"{r['price'][k]:g}" for k in PRICE_ANSWERS)
        cells = [("Buyer", f"{esc(r['buyer_id'])} {esc(r['name'])}", ""),
                 ("Segment", esc(r["segment"]), ""),
                 ("Budget", money(r["budget"], r["currency"]), ' class="num"'),
                 ("Decision", f'<span class="{r["decision"]}">{esc(decision)}</span>', ""),
                 ("Intent", str(r["intent"]), ' class="num"'),
                 ("Reason", esc(r["reason"]), ""),
                 ("In their words", f"&ldquo;{esc(r['quote'])}&rdquo;", ""),
                 ("Gives up", esc(r["give_up"]) or "-", ""),
                 ("Price answers", prices, ' class="num"')]
        tds = "".join(f'<td data-label="{label}"{attr}>{value}</td>' for label, value, attr in cells)
        rows.append(f'<tr data-segment="{esc(r["segment"])}" data-decision="{r["decision"]}" '
                    f'data-reason="{esc(r["reason"])}">{tds}</tr>')
    heads = "".join(f"<th scope=\"col\">{h}</th>" for h in (
        "Buyer", "Segment", "Budget", "Decision", "Intent", "Reason", "In their words", "Gives up", "Price answers"))
    legend = "".join(f'<li class="{css}"><span>{label}</span></li>' for _, css, label in CURVES)
    f = data["filters"]
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Buyer panel, round {esc(rnd['label'])}</title>
<style>{PAGE_CSS}</style>
</head>
<body>
<main>
<header>
<p class="simulated" role="note">{esc(data['simulated'])}</p>
<h1>{esc(data['idea'])}</h1>
<p class="meta">Round {esc(rnd['label'])} at {money(rnd['price'], cur)}. The card read: &ldquo;{esc(rnd['offer'])}&rdquo; Interviews: {esc(how)}. Model: {esc(rnd['model'])}.</p>
</header>
<section aria-labelledby="summary">
<h2 id="summary">Summary</h2>
<dl class="summary">
{"".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in summary)}
</dl>
</section>
{checks_html(data.get('checks'))}
<section aria-labelledby="price">
<h2 id="price">Price curves</h2>
<figure>
{price_svg(data['chart'], price, cur)}
<ul class="legend">{legend}</ul>
<figcaption class="meta">Share of the {data['chart']['answers']} buyers whose answers were in order. The shaded band is the acceptable range; synthetic buyers overstate what they would pay, so read it as an upper bound.</figcaption>
</figure>
</section>
<section aria-labelledby="buyers">
<h2 id="buyers">Buyers</h2>
<form id="filters" hidden>
{select("segment", "Segment", f["segment"])}
{select("decision", "Decision", f["decision"])}
{select("reason", "Reason", f["reason"])}
<p id="count" class="count" aria-live="polite"></p>
</form>
<p class="meta">Intent runs from 1 to 5 on the judge's anchor statements. Price answers read too cheap / cheap / expensive / too expensive, in {esc(cur)}.</p>
<table>
<thead><tr>{heads}</tr></thead>
<tbody>
{chr(10).join(rows)}
</tbody>
</table>
</section>
</main>
<script>{PAGE_JS}</script>
</body>
</html>
"""


def show_page(result):
    if "errors" in result:
        return show_errors(result)
    print(f"page for {result['rows']} buyers: {result['page']} (data: {result['data']})")


@command("page", "write the page data for a round and a self-contained HTML page from it", show_page, [
    (("round_dir",), {"metavar": "ROUND_DIR"}),
    (("--buyers",), {"metavar": "FILE", "help": "buyers file (default ROUND_DIR/../../buyers.jsonl)"}),
    (("--weights",), {"metavar": "W5,W4,W3,W2,W1", "help": "intent weights, default 0.75,0.25,0.1,0.05,0.02"}),
    (("--data",), {"metavar": "FILE", "help": "page data (default ROUND_DIR/page.json)"}),
    (("--out",), {"metavar": "FILE", "help": "HTML page (default ROUND_DIR/page.html)"}),
])
def cmd_page(args):
    weights = parse_weights(args.weights)
    meta, buyers, answers, scores, errors = load_round(args.round_dir, args.buyers)
    if errors:
        return {"errors": errors}, 3
    data = page_data(args.round_dir, meta, buyers, answers, scores, weights)
    data_path = args.data or os.path.join(args.round_dir, "page.json")
    page_path = args.out or os.path.join(args.round_dir, "page.html")
    with open(data_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")
    with open(page_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(page_html(data))
    return {"data": data_path, "page": page_path, "rows": len(data["rows"])}, 0


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
