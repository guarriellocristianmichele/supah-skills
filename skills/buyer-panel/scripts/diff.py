"""Two rounds side by side: buyer by buyer on the same buyers (diff, competitor), or two halves of one panel
(split, compare). Stdlib only."""
from records import UsageError, panel_of
from tally import buy_share, buy_reasons, discounted_count, pass_reasons, price_range, reasons, share


def same_panel(round_dirs, why):
    """Refuse rounds from different panels when no buyers file says which buyers they share."""
    if len({panel_of(d) for d in round_dirs}) > 1:
        raise UsageError(why)


def delta(a, b):
    return None if a is None or b is None else round(b - a, 2)


def by_buyer(rnd):
    return {r["buyer_id"]: r for r in rnd.rows()}


# ---------------------------------------------------------------- diff

def diff_rounds(round_a, round_b, weights):
    """What moved between two rounds over the buyers answered and scored in both."""
    before, after = by_buyer(round_a), by_buyer(round_b)
    meta_a, meta_b = round_a.meta, round_b.meta
    both = [bid for bid in before if bid in after]
    flips = {"pass_to_buy": [b for b in both if before[b]["decision"] == "PASS" and after[b]["decision"] == "BUY"],
             "buy_to_pass": [b for b in both if before[b]["decision"] == "BUY" and after[b]["decision"] == "PASS"]}
    switches = [{"buyer_id": b, "from": before[b]["choice"], "to": after[b]["choice"]}
                for b in both if before[b]["choice"] != after[b]["choice"]]
    options = meta_a["options"] + [o for o in meta_b["options"] if o not in meta_a["options"]]
    choices = [{"option": o, "before": sum(before[b]["choice"] == o for b in both),
                "after": sum(after[b]["choice"] == o for b in both)} for o in options]
    rows_a, rows_b = [before[b] for b in both], [after[b] for b in both]
    return {"before": round_a.described(), "after": round_b.described(),
            "buyers": {"both": len(both), "only_before": [b for b in before if b not in after],
                       "only_after": [b for b in after if b not in before]},
            "flips": flips, "switches": switches, "choices": choices,
            "buy_share": share_shift(rows_a, rows_b, weights), "intent": intent_shift(both, before, after),
            "pass_reasons": reason_shift(rows_a, rows_b, "PASS"), "buy_reasons": reason_shift(rows_a, rows_b, "BUY"),
            "price": price_shift(meta_a, meta_b, rows_a, rows_b),
            "rows": [buyer_change(before[b], after[b]) for b in both]}


def buyer_change(a, b):
    if a["decision"] != b["decision"]:
        kind = "pass-to-buy" if b["decision"] == "BUY" else "buy-to-pass"
    else:
        kind = "switch" if a["choice"] != b["choice"] else "same"
    fields = ("choice", "decision", "intent", "reason", "quote", "give_up", "price")
    return {"buyer_id": a["buyer_id"], "name": a["name"], "segment": a["segment"], "change": kind,
            "before": {k: a[k] for k in fields}, "after": {k: b[k] for k in fields}}


def reason_shift(rows_a, rows_b, decision):
    """Top reasons in both rounds; `new` are top reasons after that were not top before, `gone` the reverse."""
    a = reasons([r for r in rows_a if r["decision"] == decision])
    b = reasons([r for r in rows_b if r["decision"] == decision])
    tags_a, tags_b = [x["reason"] for x in a], [x["reason"] for x in b]
    return {"before": a, "after": b, "new": [t for t in tags_b if t not in tags_a],
            "gone": [t for t in tags_a if t not in tags_b]}


def price_shift(meta_a, meta_b, rows_a, rows_b):
    a, b = price_range(rows_a), price_range(rows_b)
    return {"card": {"before": meta_a["price"], "after": meta_b["price"], "change": delta(meta_a["price"],
                                                                                        meta_b["price"]),
                     "currency": meta_b["currency"]},
            "before": a, "after": b,
            "range_change": [delta(a["range"][0], b["range"][0]), delta(a["range"][1], b["range"][1])]
            if a["range"] and b["range"] else None,
            "optimal_change": delta(a["optimal"], b["optimal"]),
            "indifference_change": delta(a["indifference"], b["indifference"])}


def share_shift(rows_a, rows_b, weights):
    """BUY share in both rounds over the same buyers; changes from the counts, not the rounded shares."""
    n = len(rows_a)
    a, b = buy_share(rows_a, weights), buy_share(rows_b, weights)
    for s in (a, b):
        del s["weights"]
    return {"before": a, "after": b, "raw_change": share(b["buy"] - a["buy"], n),
            "discounted_change": share(discounted_count(rows_b, weights) - discounted_count(rows_a, weights), n),
            "scheme": weights["scheme"]}


def intent_shift(both, before, after):
    n = len(both)
    total_a, total_b = sum(before[b]["intent"] for b in both), sum(after[b]["intent"] for b in both)
    return {"before": share(total_a, n), "after": share(total_b, n), "change": share(total_b - total_a, n),
            "up": [b for b in both if after[b]["intent"] > before[b]["intent"]],
            "down": [b for b in both if after[b]["intent"] < before[b]["intent"]],
            "same": sum(after[b]["intent"] == before[b]["intent"] for b in both)}


# ---------------------------------------------------------------- competitor

def competitor_moves(round_a, round_b, diff):
    """Who switched to the competitor ROUND_B names, who left it, and who stayed on each option and why."""
    named = round_b.meta.get("competitor")
    if not isinstance(named, dict):
        raise UsageError("ROUND_B's round.json must name the competitor it added or repriced: "
                         "\"competitor\": {\"name\", \"price\"} and \"was\" for a reprice")
    name = named["name"]
    if name in round_a.meta["options"] and "was" not in named:
        raise UsageError(f"{name} is in ROUND_A too, so this is a reprice: give the price it had there as \"was\"")
    if name not in round_a.meta["options"] and "was" in named:
        raise UsageError(f"{name} is not in ROUND_A, so it was added: drop \"was\"")
    rows = diff["rows"]
    stayed = []
    for option in [c["option"] for c in diff["choices"]]:
        held = [r for r in rows if r["before"]["choice"] == option and r["after"]["choice"] == option]
        if held:
            stayed.append({"option": option, "buyers": [r["buyer_id"] for r in held],
                           "reasons": reasons([r["after"] for r in held], top=None)})
    chosen = next(c for c in diff["choices"] if c["option"] == name)
    return {
        "name": name, "change": "repriced" if "was" in named else "added",
        "price": {"before": named.get("was"), "after": named["price"]},
        "chosen": {"before": chosen["before"], "after": chosen["after"]},
        "switched_to": [{"buyer_id": r["buyer_id"], "from": r["before"]["choice"], "reason": r["after"]["reason"],
                         "quote": r["after"]["quote"]}
                        for r in rows if r["after"]["choice"] == name and r["before"]["choice"] != name],
        "left": [{"buyer_id": r["buyer_id"], "to": r["after"]["choice"], "reason": r["after"]["reason"],
                  "quote": r["after"]["quote"]}
                 for r in rows if r["before"]["choice"] == name and r["after"]["choice"] != name],
        "other_switches": [s for s in diff["switches"] if name not in (s["from"], s["to"])],
        "stayed": stayed,
    }


# ---------------------------------------------------------------- split and compare

def halves(buyers, rng):
    """Two halves balanced by segment: each segment's buyers shuffled and dealt alternately, and a segment's
    odd buyer goes to A, then B, then A..., segments in order of first appearance, so the halves differ by
    at most one buyer overall and within every segment."""
    by_segment = {}
    for b in buyers:
        by_segment.setdefault(b["segment"], []).append(b)
    a, b, spare_to_a, counts = [], [], True, []
    for segment, group in by_segment.items():
        group = group[:]
        rng.shuffle(group)
        pairs = len(group) - len(group) % 2
        to_a, to_b = group[0:pairs:2], group[1:pairs:2]
        if len(group) % 2:
            (to_a if spare_to_a else to_b).append(group[-1])
            spare_to_a = not spare_to_a
        a += to_a
        b += to_b
        counts.append({"segment": segment, "a": len(to_a), "b": len(to_b)})
    return a, b, counts


def half_summary(meta, rows, weights):
    s = buy_share(rows, weights)
    segments = {}
    for r in rows:
        segments[r["segment"]] = segments.get(r["segment"], 0) + 1
    return {"label": meta["label"], "variant": meta.get("variant"), "offer": meta["offer"], "price": meta["price"],
            "currency": meta["currency"], "buyers": s["buyers"], "buy": s["buy"], "raw": s["raw"],
            "discounted": s["discounted"],
            "choices": [{"option": o, "count": sum(r["choice"] == o for r in rows)} for o in meta["options"]],
            "pass_reasons": pass_reasons(rows), "buy_reasons": buy_reasons(rows),
            "price_range": price_range(rows), "segments": segments}


def compare_halves(round_a, round_b, weights):
    rows_a, rows_b = by_buyer(round_a), by_buyer(round_b)
    both = [bid for bid in rows_a if bid in rows_b]
    if both:
        raise UsageError(f"each buyer sees one variant; {', '.join(both)} answered both rounds")
    a = half_summary(round_a.meta, list(rows_a.values()), weights)
    b = half_summary(round_b.meta, list(rows_b.values()), weights)
    na, nb = a["buyers"], b["buyers"]
    if not na or not nb:
        raise UsageError("each round needs scored answers from its half of the panel")
    raw = share(b["buy"] * na - a["buy"] * nb, na * nb)
    pooled = (a["buy"] + b["buy"]) / (na + nb)
    se = round((pooled * (1 - pooled) * (1 / na + 1 / nb)) ** 0.5, 4)
    names = list(a["segments"]) + [s for s in b["segments"] if s not in a["segments"]]
    segments = [{"segment": s, "a": a["segments"].get(s, 0), "b": b["segments"].get(s, 0)} for s in names]
    discounted = share(discounted_count(rows_b.values(), weights) * na
                       - discounted_count(rows_a.values(), weights) * nb, na * nb)
    return {"a": a, "b": b, "scheme": weights["scheme"],
            "difference": {"raw": raw, "discounted": discounted},
            "noise": {"standard_error": se, "one_buyer": share(1, min(na, nb))},
            "within_noise": abs(raw) <= 2 * se,
            "higher": None if raw == 0 else (b["label"] if raw > 0 else a["label"]),
            "segments": segments, "balanced": all(abs(s["a"] - s["b"]) <= 1 for s in segments)}
