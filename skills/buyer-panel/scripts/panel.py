#!/usr/bin/env python3
"""Validate and aggregate a synthetic buyer panel kept in the panel ledger.

Usage:
  panel.py [--json] validate FILE...
  panel.py [--json] variety PANEL_DIR
  panel.py [--json] deal --buyers FILE --options ID,ID,... [--batch-size N] [--seed N] --out FILE
  panel.py [--json] reactions ROUND_DIR [--seed N] --out FILE
  panel.py [--json] aggregate ROUND_DIR [--buyers FILE] [--weights W5,W4,W3,W2,W1] [--out FILE]
  panel.py [--json] checks ROUND_DIR [--buyers FILE] [--advisory] [--out FILE]
  panel.py [--json] diff ROUND_A ROUND_B [--buyers FILE] [--out FILE]
  panel.py [--json] prices ROUND_DIR [--buyers FILE]
  panel.py [--json] revenue ROUND_DIR ROUND_DIR... [--buyers FILE]
  panel.py [--json] page ROUND_DIR [--buyers FILE] [--out FILE]
  panel.py [--json] quotes ROUND_DIR [--buyers FILE] [--type SEGMENT] [--seed N] [--holdout-out FILE]
                   [--out FILE]
  panel.py [--json] objections ROUND_DIR [--buyers FILE]
  panel.py [--json] split --buyers FILE --options ID,ID,... [--batch-size N] [--seed N] --out-a FILE --out-b FILE
  panel.py [--json] compare ROUND_A ROUND_B [--buyers FILE] [--out FILE]
  panel.py [--json] competitor ROUND_A ROUND_B [--buyers FILE] [--out FILE]
  panel.py [--json] ground FILE [--panel DIR]

validate   checks records against the schemas in RECORDS.md; the kind comes from the file name
           (buyers.jsonl, answers.jsonl or answers/*.jsonl, scores.jsonl, brief.json, plan.json, round.json,
           test.json).
variety    checks the panel's buyers before any interview: their count against the plan's size, each
           segment's share against the plan's, budgets spread across each segment's range, and no name or
           objection written twice (thresholds and reasons in BUYERS.md); exits 1 on a failure. With brief.json
           beside them it also prints the reach: buyers whose budget is at or above the brief's price, by
           segment, a fact for the user to weigh that never fails.
deal       gives every buyer the options in its own random order and puts buyers in batches mixed across
           segments, for the interviews; writes one card line per buyer to --out.
reactions  writes what the judge may see: buyer id and free reaction only, in shuffled order.
aggregate  turns one round (round.json, answers, scores) into numbers: raw and discounted BUY share with the
           weighting scheme named, reasons with counts, buyer types, and the Van Westendorp price range with
           out-of-order answers dropped and counted. Buyers default to ROUND_DIR/../../buyers.jsonl. With a
           grounding.jsonl in the project's ledger (ROUND_DIR/../../..), it adds the corrected figure from the
           latest grounding; so does every subcommand below that prints a BUY share.
checks     flags a round that should not be trusted: intent spread too low, one reason tag given by too many
           buyers, reactions in the same words, praise too dense, BUY share above the plausible bound, the
           option shown first chosen too often (thresholds and sources in READING.md); prints the report's
           Checks section and, on a failure, its verdict line. --advisory, for a screening or try-out
           round (a subset of the panel), states the failures in an advisory line instead and exits 0.
diff       compares two rounds of the same panel over the buyers answered and scored in both: PASS to BUY
           and back, every change of option (between competitors too), choices per option, BUY share,
           intent, new and gone top reasons, and the card price and price range moved.
prices     proposes three prices from a round's price range: its low end, the indifference point (the
           middle of the range when that point falls outside it) and its high end; none when there is no range.
revenue    compares price rounds of one panel that differ only in price: raw and discounted buyers at each
           price, revenue as price times discounted buyers, revenue relative to the best, and the price that
           earns most (on a tie, the lower one), next to the one raw buyers alone would pick. Every price counts
           the same buyers: one missing an answer or a score in any round is left out of all, and listed.
page       writes the page data for a round (ROUND_DIR/page.json) and a self-contained HTML page
           from it (default ROUND_DIR/page.html): the simulated-panel line, the summary, any checks found in
           ROUND_DIR/summary.json or ROUND_DIR/checks.json, the price curves as inline SVG and the buyer
           table with filters.
quotes     for the pitch: one buyer type's quotes and reactions with buyer ids (the type named, or the most
           likely to buy), and the buyers held out to try the pitch on: half the type (rounded down), dealt so both halves
           hold buyers and passers, with their first-round decisions; their own words are never printed.
objections the round's top three pass reasons for the real-test kit, each with the buyers who gave it, their words,
           current solution and last spend, plus the likely buyer type and the predicted BUY share.
split      for compare: two halves of the panel balanced by segment (a segment's odd buyer to A, then B,
           in turn), each half's cards dealt as `deal` does, one cards file per variant.
compare    two variants, each shown to one half: BUY share raw and discounted on each side, B minus A, the
           noise beside it (one standard error of the difference, and what one buyer moves), shown and never
           tested, reasons and choices per side, and the segments on each side. A buyer in both rounds is
           refused.
competitor the round diff after ROUND_B added or repriced the competitor its round.json names, plus who
           switched to it, who left it, and who stayed on each option with the reasons that held them.
ground     compares real results (PANEL/real/<label>.json: a smoke test, interviews or a pre-sale) with the
           discounted BUY share of the round they tested, at the same price, and stores the ratio of real to
           predicted in PANEL/../grounding.jsonl, the project's ledger, naming the panel (one line per panel and
           label; importing a label again replaces it).

Exit codes: 0 done; 1 a check failed (checks, variety); 2 bad usage; 3 invalid records (nothing is aggregated or checked
from them). This file is the command line and its Markdown; the modules beside it hold the records
(records.py), the numbers (tally.py), the checks (checks.py), two rounds side by side (diff.py), the
grounding (ground.py) and the page (page.py). Stdlib only.
"""
import argparse
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import checks  # noqa: E402  (sibling modules, listed in the docstring)
import diff  # noqa: E402
import ground  # noqa: E402
import page  # noqa: E402
import tally  # noqa: E402
from records import (NOTHING, OFFER, PRICE_ANSWERS, RecordErrors, UsageError, load, load_round,  # noqa: E402
                     option_errors, plan_fit_errors, read_jsonl, validate_file, write_json, write_jsonl)
from tally import WEIGHTS, parse_weights, pct  # noqa: E402

COMMANDS = {}


def command(name, summary, show, arguments=()):
    """Register a subcommand. `arguments` are (flags, options) pairs for argparse; the function gets the parsed
    args and returns (result, exit code), or raises RecordErrors or UsageError; `show` prints the result when
    --json is not given."""
    def wrap(fn):
        COMMANDS[name] = (fn, summary, show, arguments)
        return fn
    return wrap


BUYERS = (("--buyers",), {"metavar": "FILE", "help": "buyers file (default ROUND_DIR/../../buyers.jsonl)"})
BUYERS_BOTH = (("--buyers",), {"metavar": "FILE", "help": "buyers file for both (default ROUND_A/../../buyers.jsonl)"})
WEIGHTS_OPTION = (("--weights",), {"metavar": "W5,W4,W3,W2,W1",
                                   "help": "intent weights, default 0.75,0.25,0.1,0.05,0.02"})
OUT_JSON = (("--out",), {"metavar": "FILE", "help": "also write the JSON result here"})
SEED = (("--seed",), {"type": int, "metavar": "N", "help": "random seed, recorded (default: a fresh one)"})
BATCH_SIZE = (("--batch-size",), {"type": int, "default": 5, "metavar": "N", "help": "buyers per interview context (5)"})


def fresh_seed(seed):
    return seed if seed is not None else random.SystemRandom().randrange(10 ** 6)


def option_ids(text):
    options = [o.strip() for o in text.split(",") if o.strip()]
    problems = option_errors(options)
    if problems:
        raise UsageError(f"--options {problems[0][1]}")
    return options


def batch_size(n):
    if n < 1:
        raise UsageError("--batch-size must be 1 or more")
    return n


# ---------------------------------------------------------------- Markdown helpers

def show_errors(result):
    for e in result["errors"]:
        print(f"{e['file']}:{e['line']}: {e['field'] or '-'}: {e['problem']}")


def cell(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def signed_points(x):
    return "n/a" if x is None else f"{x * 100:+.1f} points"


def id_list(xs):
    return ", ".join(xs) or "none"


def decision_label(row):
    return row["decision"] if row["choice"] in (OFFER, NOTHING) else f"PASS ({row['choice']})"


def reason_counts(items):
    return ", ".join(f"{r['reason']} {r['count']}" for r in items) or "none"


# ---------------------------------------------------------------- validate

def show_validate(results):
    for r in results:
        print(f"{r['file']}: {r['kind'] or '?'}, {r['records']} records, {len(r['errors'])} errors")
        for e in r["errors"]:
            print(f"  line {e['line']}: {e['field'] or '-'}: {e['problem']}")


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
            r["errors"] = plan_fit_errors(r["file"], r["data"], r["lines"], plan["data"])
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


def deal_cards(buyers, options, size, rng):
    """Each buyer's own option order, batches mixed across segments."""
    cards = []
    for i, buyer in enumerate(mixed_order(buyers)):
        shown = options[:]
        rng.shuffle(shown)
        cards.append({"buyer_id": buyer["id"], "batch": i // size + 1, "options": shown})
    return cards


def show_deal(result):
    print(f"{result['buyers']} cards in {result['batches']} batches of up to {result['batch_size']}, "
          f"seed {result['seed']}: {result['out']}")


@command("deal", "give each buyer the options in its own order, in batches mixed across segments", show_deal, [
    (("--buyers",), {"required": True, "metavar": "FILE"}),
    (("--options",), {"required": True, "metavar": "ID,ID,...",
                      "help": "option ids: offer, nothing and the alternatives' names"}),
    BATCH_SIZE, SEED,
    (("--out",), {"required": True, "metavar": "FILE", "help": "where to write one card line per buyer"}),
])
def cmd_deal(args):
    options, size = option_ids(args.options), batch_size(args.batch_size)
    buyers = load(args.buyers, "buyers", "a buyers.jsonl file")["data"]
    seed = fresh_seed(args.seed)
    cards = deal_cards(buyers, options, size, random.Random(seed))
    write_jsonl(args.out, cards)
    return {"out": args.out, "buyers": len(cards), "batches": cards[-1]["batch"] if cards else 0,
            "batch_size": size, "seed": seed}, 0


def show_reactions(result):
    print(f"{result['reactions']} reactions for the judge, seed {result['seed']}: {result['out']}")


@command("reactions", "write the judge's input: buyer id and reaction only, shuffled", show_reactions, [
    (("round_dir",), {"metavar": "ROUND_DIR"}), BUYERS, SEED, (("--out",), {"required": True, "metavar": "FILE"}),
])
def cmd_reactions(args):
    rnd = load_round(args.round_dir, args.buyers)
    seed = fresh_seed(args.seed)
    shown = [{"buyer_id": bid, "reaction": a["reaction"]} for bid, a in rnd.answers.items()]
    random.Random(seed).shuffle(shown)
    write_jsonl(args.out, shown)
    return {"out": args.out, "reactions": len(shown), "seed": seed}, 0


# ---------------------------------------------------------------- aggregate

def add_corrected(into, rnd, rows, weights=WEIGHTS):
    """Put the project's latest grounding, applied to these rows of the round, under `corrected` in `into`;
    nothing without a grounding."""
    figure = ground.corrected_figure(rnd.dir, rows, weights)
    if figure:
        into["corrected"] = figure
    return into


def show_corrected(*named):
    """One `Corrected` line for (label or None, corrected) pairs that share one grounding; nothing without it."""
    named = [(label, c) for label, c in named if c]
    if not named:
        return
    c = named[0][1]
    source = (f"grounding {c['grounding']} of panel {c['panel']} ({c['test']} on round {c['round']}, "
              f"{c['acted']} of {c['reached']}, {c['date']})")
    if all(x["figure"] is None for _, x in named):
        print(f"Corrected: n/a, {c.get('problem', 'no buyers in this round')}; {source}")
        return
    figures = ", ".join((f"{label} " if label else "") + pct(x["figure"]) for label, x in named)
    print(f"Corrected: {figures} {c['measure']}, discounted x {c['ratio']:g} from {source}")


def show_aggregate(result):
    """Markdown for the report: the summary, then the full buyer table."""
    s, p, rnd = result["buy_share"], result["price"], result["round"]
    cur = rnd["currency"]
    print(f"BUY {s['buy']} of {s['buyers']}: raw {pct(s['raw'])}, discounted {pct(s['discounted'])} "
          f"({s['weights']['scheme']})")
    show_corrected((None, result.get("corrected")))
    print(f"Top reasons to pass: {reason_counts(result['pass_reasons'])}")
    print(f"Top reasons to buy: {reason_counts(result['buy_reasons'])}")
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
        prices = " / ".join(f"{r['price'][k]:g}" for k in PRICE_ANSWERS)
        print(f"| {r['buyer_id']} {cell(r['name'])} | {cell(r['segment'])} | {r['budget']:g} {r['currency']} | "
              f"{decision_label(r)} | {r['intent']} | {r['reason']} | \"{cell(r['quote'])}\" | "
              f"{cell(r['give_up']) or '-'} | {prices} |")


@command("aggregate", "turn one round into numbers", show_aggregate, [
    (("round_dir",), {"metavar": "ROUND_DIR"}), BUYERS, WEIGHTS_OPTION, OUT_JSON,
])
def cmd_aggregate(args):
    weights = parse_weights(args.weights)
    rnd = load_round(args.round_dir, args.buyers)
    result = tally.summary(rnd, weights)
    add_corrected(result, rnd, result["rows"], weights)
    if args.out:
        write_json(args.out, result)
    return result, 0


# ---------------------------------------------------------------- checks

def show_check_table(result):
    print("| check | what it measures | value | threshold | result |")
    print("|---|---|---|---|---|")
    for c in result["checks"]:
        value = "n/a" if c["value"] is None else f"{c['value']:g}"
        state = "pass" if c["passed"] else "warn" if c.get("advisory") else "FAIL"
        print(f"| {c['name']} | {c['what']} | {value} | {c['threshold']} | {state} |")
    print()
    if result["verdict_line"]:
        print(result["verdict_line"])
    if result.get("warned"):
        print("Advisory, not part of the verdict: " + ", ".join(checks.LABELS[n] for n in result["warned"]) + ".")


def show_checks(result):
    """Markdown for the report's Checks section."""
    show_check_table(result)
    keep = next((c for c in result["checks"] if c["name"] == "keep"), None)
    if keep and not keep["passed"]:
        print(f"Paying buyers who chose nothing: {id_list(keep['buyers'])}")
    print(result["segments"]["why"])


def show_variety(result):
    show_check_table(result)
    for c in result["checks"]:
        if c.get("buyers"):
            print(f"{c['what'].capitalize()}: {id_list(c['buyers'])}")
    r = result.get("reach")
    if r:
        by_segment = ", ".join(f"{s['name']} {s['reached']} of {s['buyers']}" for s in r["segments"])
        print(f"Reach at {r['price']:g} {r['currency']} (the brief's price, for you to weigh, not a check): "
              f"{r['reached']} of {r['buyers']} buyers have a budget at or above it; by segment: {by_segment}.")


@command("variety", "check the panel's buyers for variety against the plan, before any interview", show_variety, [
    (("panel",), {"metavar": "PANEL_DIR",
                  "help": "the panel folder, holding buyers.jsonl and plan.json (and brief.json for the reach line)"}),
])
def cmd_variety(args):
    buyers = load(os.path.join(args.panel, "buyers.jsonl"), "buyers", "a buyers.jsonl file")
    plan = load(os.path.join(args.panel, "plan.json"), "plan", "a plan.json file")["data"]
    outside = plan_fit_errors(buyers["file"], buyers["data"], buyers["lines"], plan)
    if outside:
        raise RecordErrors(outside)
    result = checks.run_variety(buyers["data"], plan)
    brief_path = os.path.join(args.panel, "brief.json")
    if os.path.exists(brief_path):
        result["reach"] = checks.reach(buyers["data"], plan, load(brief_path, "brief", "a brief.json file")["data"])
    return result, 1 if result["failed"] else 0


@command("checks", "flag a round that is too uniform, too agreeable or order-biased", show_checks, [
    (("round_dir",), {"metavar": "ROUND_DIR"}), BUYERS,
    (("--advisory",), {"action": "store_true",
                       "help": "a screening or try-out round: state failures, set no verdict, exit 0"}),
    OUT_JSON,
])
def cmd_checks(args):
    result = checks.run_checks(load_round(args.round_dir, args.buyers), args.advisory)
    if args.out:
        write_json(args.out, result)
    return result, 1 if result["failed"] and not args.advisory else 0


# ---------------------------------------------------------------- diff

def show_diff(result):
    """Markdown for the report: what moved between the rounds, then every buyer compared."""
    a, b = result["before"]["label"], result["after"]["label"]
    s, i, p = result["buy_share"], result["intent"], result["price"]
    print(f"{a} -> {b}: {result['buyers']['both']} buyers in both rounds")
    for label, key in ((a, "only_before"), (b, "only_after")):
        if result["buyers"][key]:
            print(f"Only in {label} (not compared): {id_list(result['buyers'][key])}")
    print(f"BUY {s['before']['buy']} of {s['before']['buyers']} -> {s['after']['buy']} of {s['after']['buyers']}: "
          f"raw {pct(s['before']['raw'])} -> {pct(s['after']['raw'])} ({signed_points(s['raw_change'])}), "
          f"discounted {pct(s['before']['discounted'])} -> {pct(s['after']['discounted'])} "
          f"({signed_points(s['discounted_change'])}), weights {s['scheme']}")
    if "corrected" in result:
        show_corrected((a, result["corrected"]["before"]), (b, result["corrected"]["after"]))
    print(f"PASS to BUY: {id_list(result['flips']['pass_to_buy'])}. "
          f"BUY to PASS: {id_list(result['flips']['buy_to_pass'])}.")
    print("Switches: " + (", ".join(f"{x['buyer_id']} {x['from']} -> {x['to']}" for x in result["switches"])
                          or "none"))
    print("Choices: " + ", ".join(f"{c['option']} {c['before']} -> {c['after']}" for c in result["choices"]))
    if i["before"] is not None:
        print(f"Mean intent {i['before']:.2f} -> {i['after']:.2f} ({i['change']:+.2f}): up {id_list(i['up'])}; "
              f"down {id_list(i['down'])}; {i['same']} the same")
    for key, label in (("pass_reasons", "Top reasons to pass"), ("buy_reasons", "Top reasons to buy")):
        r = result[key]
        print(f"{label}: {reason_counts(r['before'])} -> {reason_counts(r['after'])} "
              f"(new: {id_list(r['new'])}; gone: {id_list(r['gone'])})")
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


SAME_BUYERS = "the two rounds belong to different panels; diff compares rounds of the same buyers"


def two_rounds(args, why):
    if args.buyers is None:
        diff.same_panel((args.before, args.after), why)
    return load_round(args.before, args.buyers), load_round(args.after, args.buyers)


def diff_with_corrected(round_a, round_b):
    """The round diff, with the corrected figure of each round over the buyers compared when grounded."""
    result = diff.diff_rounds(round_a, round_b, WEIGHTS)
    both = {r["buyer_id"] for r in result["rows"]}
    sides = {side: add_corrected({}, rnd, [r for r in rnd.rows() if r["buyer_id"] in both]).get("corrected")
             for side, rnd in (("before", round_a), ("after", round_b))}
    if sides["before"]:
        result["corrected"] = sides
    return result


@command("diff", "compare two rounds of the same buyers, buyer by buyer", show_diff, [
    (("before",), {"metavar": "ROUND_A"}), (("after",), {"metavar": "ROUND_B"}), BUYERS_BOTH,
    OUT_JSON,
])
def cmd_diff(args):
    round_a, round_b = two_rounds(args, SAME_BUYERS)
    result = diff_with_corrected(round_a, round_b)
    if args.out:
        write_json(args.out, result)
    return result, 0


def show_competitor(result):
    show_diff(result)
    c = result["competitor"]
    cur = result["after"]["currency"]
    what = (f"added at {c['price']['after']:g} {cur}" if c["change"] == "added"
            else f"repriced {c['price']['before']:g} -> {c['price']['after']:g} {cur}")
    print()
    print(f"{c['name']} {what}: chosen by {c['chosen']['before']} -> {c['chosen']['after']} buyers.")
    print(f"Switched to {c['name']}: " + ("; ".join(
        f"{x['buyer_id']} from {x['from']} ({x['reason']}: \"{x['quote']}\")" for x in c["switched_to"]) or "none"))
    print(f"Left {c['name']}: " + ("; ".join(
        f"{x['buyer_id']} to {x['to']} ({x['reason']}: \"{x['quote']}\")" for x in c["left"]) or "none"))
    if c["other_switches"]:
        print("Other switches: " + ", ".join(f"{x['buyer_id']} {x['from']} -> {x['to']}" for x in c["other_switches"]))
    print("Stayed: " + ("; ".join(f"{g['option']} {id_list(g['buyers'])} ({reason_counts(g['reasons'])})"
                                  for g in c["stayed"]) or "none"))


@command("competitor", "the round diff after a competitor was added or repriced, with who switched and who stayed",
         show_competitor, [
             (("before",), {"metavar": "ROUND_A"}),
             (("after",), {"metavar": "ROUND_B", "help": "the round whose round.json names the competitor"}),
             BUYERS_BOTH, OUT_JSON,
         ])
def cmd_competitor(args):
    round_a, round_b = two_rounds(args, SAME_BUYERS)
    result = diff_with_corrected(round_a, round_b)
    result["competitor"] = diff.competitor_moves(round_a, round_b, result)
    if args.out:
        write_json(args.out, result)
    return result, 0


# ---------------------------------------------------------------- price

def price_round(rnd, weights, keep):
    """One price round's numbers over the buyers in `keep`: raw and discounted buyers, and revenue."""
    rows = [r for r in rnd.rows() if r["buyer_id"] in keep]
    s = tally.buy_share(rows, weights)
    likely = tally.discounted_count(rows, weights)
    meta = rnd.meta
    numbers = {"label": meta["label"], "price": meta["price"], "currency": meta["currency"], "buyers": s["buyers"],
               "buy": s["buy"], "raw": s["raw"], "discounted": s["discounted"],
               "discounted_buyers": round(likely, 4), "revenue": round(meta["price"] * likely, 2),
               "raw_revenue": round(meta["price"] * s["buy"], 2)}
    return add_corrected(numbers, rnd, rows, weights)


def earns_most(rounds, key):
    """The round with the highest `key`; on a tie the lower price, which reaches more buyers for the same money."""
    top = max(rounds, key=lambda r: (r[key], -r["price"]))
    return {"label": top["label"], "price": top["price"], "currency": top["currency"], "revenue": top[key]}


def show_revenue(result):
    """Markdown for the price report: the pick, the caveats, then one row per price."""
    best, raw, cur = result["best"], result["best_raw"], result["best"]["currency"]
    print(f"Earns most: {best['price']:g} {cur} ({best['label']}), revenue {best['revenue']:g} {cur} "
          f"(price times discounted buyers, of {result['buyers']} buyers; {result['weights']['scheme']})")
    if raw["price"] != best["price"]:
        print(f"The raw buyers alone would pick {raw['price']:g} {cur}; stated intent overstates purchase, "
              f"so the pick rests on discounted buyers")
    print("Prices are an upper bound: synthetic buyers state willingness to pay two to three times too high")
    if result["left_out"]:
        print(f"Left out of every price (missing an answer or a score in some round): {', '.join(result['left_out'])}")
    print()
    print("| price | round | BUY raw | BUY discounted | discounted buyers | revenue | relative revenue |")
    print("|---|---|---|---|---|---|---|")
    for r in result["rounds"]:
        print(f"| {r['price']:g} {cur} | {r['label']} | {r['buy']} of {r['buyers']} ({pct(r['raw'])}) | "
              f"{pct(r['discounted'])} | {r['discounted_buyers']:g} | {r['revenue']:g} {cur} | {pct(r['relative'])} |")
    print()
    show_corrected(*((r["label"], r.get("corrected")) for r in result["rounds"]))


@command("revenue", "compare price rounds of one panel: buyers and revenue at each price", show_revenue, [
    (("round_dirs",), {"nargs": "+", "metavar": "ROUND_DIR"}), BUYERS,
])
def cmd_revenue(args):
    if len(args.round_dirs) < 2:
        raise UsageError("revenue compares two or more price rounds of one panel")
    if args.buyers is None:
        diff.same_panel(args.round_dirs, "price rounds must belong to one panel (the same buyers)")
    loaded, errors = [], []
    for d in args.round_dirs:
        try:
            loaded.append(load_round(d, args.buyers))
        except RecordErrors as e:
            errors += e.errors
    if errors:
        raise RecordErrors(errors)
    first = loaded[0].meta
    for rnd in loaded[1:]:
        for field in ("offer", "currency", "options"):
            if rnd.meta[field] != first[field]:
                raise UsageError(f"price rounds differ only in price: {rnd.label} has another {field} "
                                 f"than {first['label']}")
    prices = [rnd.meta["price"] for rnd in loaded]
    if len(set(prices)) != len(prices):
        raise UsageError("each price round needs its own price")
    panel = loaded[0].buyers
    keep = {bid for bid in panel if all(bid in rnd.answers and bid in rnd.scores for rnd in loaded)}
    rounds = sorted((price_round(rnd, WEIGHTS, keep) for rnd in loaded), key=lambda r: r["price"])
    best, best_raw = earns_most(rounds, "revenue"), earns_most(rounds, "raw_revenue")
    for r in rounds:
        r["relative"] = tally.share(r["revenue"], best["revenue"])
    return {"rounds": rounds, "best": best, "best_raw": best_raw, "buyers": len(keep),
            "left_out": [bid for bid in panel if bid not in keep], "weights": WEIGHTS, "upper_bound": True}, 0


def show_prices(result):
    if result["prices"] is None:
        print(f"{result['from']} has no price range ({result['dropped']} out-of-order answers dropped): "
              f"ask for three prices")
    else:
        print(f"From {result['from']}'s price range (an upper bound): "
              + " / ".join(f"{p:g}" for p in result["prices"]) + f" {result['currency']}")


@command("prices", "propose three prices (low, mid, high) from a round's price range", show_prices, [
    (("round_dir",), {"metavar": "ROUND_DIR"}), BUYERS,
])
def cmd_prices(args):
    rnd = load_round(args.round_dir, args.buyers)
    p = tally.price_range(rnd.rows())
    out = {"from": rnd.label, "currency": rnd.meta["currency"], "prices": None, "dropped": len(p["dropped"]),
           "upper_bound": True}
    if p["range"]:
        low, high = p["range"]
        inside = p["indifference"] is not None and low < p["indifference"] < high
        out["prices"] = [low, p["indifference"] if inside else round((low + high) / 2, 2), high]
    return out, 0


# ---------------------------------------------------------------- page

def show_page(result):
    print(f"page for {result['rows']} buyers: {result['page']} (data: {result['data']})")


@command("page", "write the page data for a round and a self-contained HTML page from it", show_page, [
    (("round_dir",), {"metavar": "ROUND_DIR"}), BUYERS,
    (("--out",), {"metavar": "FILE", "help": "HTML page (default ROUND_DIR/page.html)"}),
])
def cmd_page(args):
    data = page.page_data(load_round(args.round_dir, args.buyers), WEIGHTS)
    data_path = os.path.join(args.round_dir, "page.json")
    page_path = args.out or os.path.join(args.round_dir, "page.html")
    write_json(data_path, data)
    with open(page_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(page.page_html(data))
    return {"data": data_path, "page": page_path, "rows": len(data["rows"])}, 0


# ---------------------------------------------------------------- pitch

def split_type(rows, holdout, rng):
    """Sources and holdout for one buyer type: BUYs first, each group shuffled, then dealt alternately so both
    halves hold buyers who bought and buyers who passed. The holdout takes `holdout` buyers."""
    buys = [r for r in rows if r["decision"] == "BUY"]
    passes = [r for r in rows if r["decision"] != "BUY"]
    rng.shuffle(buys)
    rng.shuffle(passes)
    dealt = buys + passes
    held = dealt[1::2][:holdout]
    held_ids = {r["buyer_id"] for r in held}
    return [r for r in dealt if r["buyer_id"] not in held_ids], held


def show_quotes(result):
    """Markdown for the pitch writer: the type, its words with buyer ids, and who is held out."""
    f = result["first_round"]
    print(f"Type {result['type']} ({result['picked']}) in round {result['round']}, seed {result['seed']}. "
          "Other types: " + (", ".join(f"{t['segment']} {t['buy']} of {t['buyers']}" for t in result["types"]
                                       if t["segment"] != result["type"]) or "none"))
    print("Their words (borrow only from these, quoted, with the buyer id):")
    for q in result["quotes"]:
        print(f"- {q['buyer_id']} {q['name']} ({q['decision']}, intent {q['intent']}, {q['reason']}): "
              f"\"{q['quote']}\" Reaction: \"{q['reaction']}\"")
    print(f"Held out for the try-out, first round BUY {f['buy']} of {f['buyers']}: raw {pct(f['raw'])}, "
          f"discounted {pct(f['discounted'])}: " + (", ".join(
              f"{h['buyer_id']} {h['name']} ({h['decision']}, intent {h['intent']})" for h in result["holdout"])
              or "none, so the pitch cannot be tried on this type"))
    show_corrected((None, f.get("corrected")))


@command("quotes", "a buyer type's own words with buyer ids, and the buyers held out to try the pitch on",
         show_quotes, [
             (("round_dir",), {"metavar": "ROUND_DIR"}), BUYERS,
             (("--type",), {"metavar": "SEGMENT", "help": "the buyer type to pitch (default: the most likely to buy)"}),
             SEED,
             (("--holdout-out",), {"metavar": "FILE", "help": "write the held-out buyers' records here (buyers.jsonl)"}),
             OUT_JSON,
         ])
def cmd_quotes(args):
    rnd = load_round(args.round_dir, args.buyers)
    all_rows = rnd.rows()
    ranked = tally.buyer_types(all_rows, WEIGHTS, top=None)
    names = [t["segment"] for t in ranked]
    if args.type is not None and args.type not in names:
        raise UsageError(f"--type {args.type!r} is not a buyer type of this round: {', '.join(names)}")
    chosen = args.type if args.type is not None else names[0]
    rows = [r for r in all_rows if r["segment"] == chosen]
    seed = fresh_seed(args.seed)
    sources, held = split_type(rows, len(rows) // 2, random.Random(seed))
    result = {
        "round": rnd.label, "type": chosen, "picked": "most likely" if args.type is None else "named",
        "seed": seed, "types": ranked,
        "quotes": [{"buyer_id": r["buyer_id"], "name": r["name"], "decision": r["decision"], "intent": r["intent"],
                    "reason": r["reason"], "quote": r["quote"], "reaction": rnd.answers[r["buyer_id"]]["reaction"]}
                   for r in sources],
        "holdout": [{"buyer_id": r["buyer_id"], "name": r["name"], "decision": r["decision"], "choice": r["choice"],
                     "intent": r["intent"], "reason": r["reason"]} for r in held],
        "first_round": tally.buy_share(held, WEIGHTS),
    }
    add_corrected(result["first_round"], rnd, held)
    if args.holdout_out:
        write_jsonl(args.holdout_out, [rnd.buyers[r["buyer_id"]] for r in held])
    if args.out:
        write_json(args.out, result)
    return result, 0


# ---------------------------------------------------------------- test

def show_objections(result):
    p = result["predicted"]
    print(f"Round {result['round']} at {result['price']:g} {result['currency']}: BUY {p['buy']} of {p['buyers']}, "
          f"raw {pct(p['raw'])}, discounted {pct(p['discounted'])}; likely buyer type: {result['likely_type']}")
    show_corrected((None, p.get("corrected")))
    for o in result["objections"]:
        print(f"\n{o['reason']} ({o['count']})")
        for b in o["buyers"]:
            print(f"- {b['buyer_id']} ({b['segment']}; uses {b['current_solution']}, last spent "
                  f"{b['last_spend']:g} {result['currency']}): \"{b['quote']}\"")


@command("objections", "the round's top pass reasons, with each buyer's words, solution and last spend",
         show_objections, [
             (("round_dir",), {"metavar": "ROUND_DIR"}), BUYERS,
         ])
def cmd_objections(args):
    rnd = load_round(args.round_dir, args.buyers)
    result = tally.summary(rnd, WEIGHTS)
    passed = [r for r in result["rows"] if r["decision"] == "PASS"]
    objections = []
    for top in tally.reasons(passed, 3):
        objections.append(dict(top, buyers=[
            {"buyer_id": r["buyer_id"], "segment": r["segment"], "quote": r["quote"],
             "current_solution": rnd.buyers[r["buyer_id"]]["current_solution"],
             "last_spend": rnd.buyers[r["buyer_id"]]["last_spend"]}
            for r in sorted(passed, key=lambda r: r["buyer_id"]) if r["reason"] == top["reason"]]))
    s = result["buy_share"]
    meta = rnd.meta
    predicted = add_corrected({k: s[k] for k in ("buyers", "buy", "raw", "discounted")}, rnd, result["rows"])
    return {"round": meta["label"], "offer": meta["offer"], "price": meta["price"], "currency": meta["currency"],
            "predicted": predicted,
            "likely_type": result["buyer_types"][0]["segment"] if result["buyer_types"] else None,
            "objections": objections}, 0


# ---------------------------------------------------------------- compare

def show_split(result):
    print(f"Halves balanced by segment, seed {result['seed']}, batches of up to {result['batch_size']}: "
          + ", ".join(f"{s['segment']} {s['a']}/{s['b']}" for s in result["segments"]))
    for half in ("a", "b"):
        r = result[half]
        print(f"{half.upper()}: {r['buyers']} cards in {r['batches']} batches: {r['out']}")


@command("split", "split the panel into two halves balanced by segment and deal each half's cards", show_split, [
    (("--buyers",), {"required": True, "metavar": "FILE"}),
    (("--options",), {"required": True, "metavar": "ID,ID,...",
                      "help": "option ids for both halves: offer, nothing and the alternatives' names"}),
    BATCH_SIZE, SEED,
    (("--out-a",), {"required": True, "metavar": "FILE", "help": "cards for variant A's half"}),
    (("--out-b",), {"required": True, "metavar": "FILE", "help": "cards for variant B's half"}),
])
def cmd_split(args):
    options, size = option_ids(args.options), batch_size(args.batch_size)
    buyers = load(args.buyers, "buyers", "a buyers.jsonl file")["data"]
    seed = fresh_seed(args.seed)
    rng = random.Random(seed)
    half_a, half_b, counts = diff.halves(buyers, rng)
    result = {"seed": seed, "batch_size": size, "segments": counts}
    for half, members, path in (("a", half_a, args.out_a), ("b", half_b, args.out_b)):
        cards = deal_cards(members, options, size, rng)
        write_jsonl(path, cards)
        result[half] = {"out": path, "buyers": len(cards), "batches": cards[-1]["batch"] if cards else 0}
    return result, 0


def dealt_without_row(rnd):
    """Buyers dealt a card in the round's cards.jsonl with no scored answer; None without a cards file. The
    round's own `aggregate` cannot say this: it counts the other half as missing too."""
    path = os.path.join(rnd.dir, "cards.jsonl")
    if not os.path.exists(path):
        return None
    scored = {r["buyer_id"] for r in rnd.rows()}
    return [rec.get("buyer_id") for _, rec, bad in read_jsonl(path) if not bad and rec.get("buyer_id") not in scored]


def show_compare(result):
    """Markdown for the report: each side, the difference and the noise next to it, the reasons per side."""
    a, b, d, n = result["a"], result["b"], result["difference"], result["noise"]
    for key, x in (("A", a), ("B", b)):
        print(f"{key} {x['label']}: BUY {x['buy']} of {x['buyers']}, raw {pct(x['raw'])}, discounted "
              f"{pct(x['discounted'])}, at {x['price']:g} {x['currency']}. Card: \"{x['offer']}\"")
    show_corrected(*((x["label"], x.get("corrected")) for x in (a, b)))
    for key, x in (("A", a), ("B", b)):
        if x["missing"]:
            print(f"Missing in {key} {x['label']} (dealt a card, no scored answer): {id_list(x['missing'])}")
    print(f"B minus A: raw {signed_points(d['raw'])}, discounted {signed_points(d['discounted'])}. Noise: one "
          f"standard error is {n['standard_error'] * 100:.1f} points, and one buyer moves the smaller side by "
          f"{n['one_buyer'] * 100:.1f} points. Noise is shown, not tested: a difference near the noise or the "
          "one-buyer swing may be no difference.")
    print(f"Weights {result['scheme']}")
    print("Segments (A/B): " + ", ".join(f"{s['segment']} {s['a']}/{s['b']}" for s in result["segments"])
          + ("" if result["balanced"] else ". Not balanced: a segment differs by more than one buyer"))
    for key, label in (("pass_reasons", "Top reasons to pass"), ("buy_reasons", "Top reasons to buy")):
        print(f"{label}: " + "; ".join(f"{name} {reason_counts(x[key])}" for name, x in (("A", a), ("B", b))))
    print("Choices: " + "; ".join(f"{name} " + ", ".join(f"{c['option']} {c['count']}" for c in x["choices"])
                                  for name, x in (("A", a), ("B", b))))
    print("Price range (upper bound): " + "; ".join(
        f"{name} " + (f"{x['price_range']['range'][0]:g} to {x['price_range']['range'][1]:g} {x['currency']}"
                      if x["price_range"]["range"] else "no crossing")
        for name, x in (("A", a), ("B", b))))


@command("compare", "compare two variants each shown to one half of the panel", show_compare, [
    (("before",), {"metavar": "ROUND_A"}), (("after",), {"metavar": "ROUND_B"}), BUYERS_BOTH,
    OUT_JSON,
])
def cmd_compare(args):
    round_a, round_b = two_rounds(args, "the two rounds belong to different panels; split one panel's buyers "
                                        "between them")
    result = diff.compare_halves(round_a, round_b, WEIGHTS)
    for half, rnd in (("a", round_a), ("b", round_b)):
        result[half]["missing"] = dealt_without_row(rnd)
        add_corrected(result[half], rnd, rnd.rows())
    if args.out:
        write_json(args.out, result)
    return result, 0


# ---------------------------------------------------------------- ground

def show_ground(result):
    m, p = result["real"], result["predicted"]
    print(f"Grounding {result['label']} ({result['test']}, {result['date']}): {m['acted']} of {m['reached']}, "
          f"{pct(m['rate'])} {m['measure']}, against round {result['round']}'s discounted {pct(p['discounted'])} "
          f"(raw {pct(p['raw'])}). Ratio {result['ratio']:g}: later rounds show discounted x {result['ratio']:g} "
          f"as the corrected figure.")


@command("ground", "compare real results with the round they test, and store the ratio", show_ground, [
    (("file",), {"metavar": "FILE", "help": "real results, PANEL/real/<label>.json"}),
    (("--panel",), {"metavar": "DIR", "help": "panel folder (default FILE/../..)"}),
])
def cmd_ground(args):
    return ground.ground(args.file, args.panel, WEIGHTS), 0


# ---------------------------------------------------------------- main

def parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
                                allow_abbrev=False)
    p.add_argument("--json", action="store_true", help="print JSON instead of a short table")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, (_, summary, _, arguments) in COMMANDS.items():
        cp = sub.add_parser(name, help=summary, allow_abbrev=False)
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
    except RecordErrors as e:
        result, code, show = {"errors": e.errors}, 3, show_errors
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
    else:
        show(result)
    return code


if __name__ == "__main__":
    sys.exit(main())
