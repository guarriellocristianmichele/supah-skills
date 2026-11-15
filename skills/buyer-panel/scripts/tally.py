"""The numbers of a round: BUY share raw and discounted, reasons, buyer types and the price range. Stdlib only."""
from records import OFFER, PRICE_ANSWERS, UsageError

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


def share(part, whole):
    return round(part / whole, 4) if whole else None


def pct(x):
    return "n/a" if x is None else f"{x * 100:.1f}%"


def discounted_count(rows, weights):
    """Buyers who chose the offer, each at the weight of their intent: the discounted count, unrounded."""
    return sum(weights["by_intent"][str(r["intent"])] for r in rows if r["choice"] == OFFER)


def buy_share(rows, weights):
    buy = sum(r["choice"] == OFFER for r in rows)
    return {"buyers": len(rows), "buy": buy, "raw": share(buy, len(rows)),
            "discounted": share(discounted_count(rows, weights), len(rows)), "weights": weights}


def reasons(rows, top=5):
    counts = {}
    for r in rows:
        counts[r["reason"]] = counts.get(r["reason"], 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [{"reason": k, "count": v} for k, v in ranked[:top]]


def pass_reasons(rows, top=5):
    return reasons([r for r in rows if r["decision"] == "PASS"], top)


def buy_reasons(rows, top=5):
    return reasons([r for r in rows if r["decision"] == "BUY"], top)


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


def in_order(answer):
    return answer["too_cheap"] < answer["cheap"] < answer["expensive"] < answer["too_expensive"]


def price_range(rows):
    """Van Westendorp price sensitivity meter (research note, "Pricing questions that work in a survey")."""
    valid = [r for r in rows if in_order(r["price"])]
    out = {"valid": len(valid), "dropped": [r["buyer_id"] for r in rows if not in_order(r["price"])],
           "upper_bound": True, "marginal_cheapness": None, "marginal_expensiveness": None, "range": None,
           "optimal": None, "indifference": None}
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


def price_curves(rows):
    """The four Van Westendorp curves at every price named, from the answers in order (as price_range)."""
    answers = [r["price"] for r in rows if in_order(r["price"])]
    n = len(answers)
    grid = sorted({a[k] for a in answers for k in PRICE_ANSWERS})
    curve = [{"price": p,
              "too_cheap": share(sum(a["too_cheap"] >= p for a in answers), n),
              "cheap": share(sum(a["cheap"] >= p for a in answers), n),
              "expensive": share(sum(a["expensive"] <= p for a in answers), n),
              "too_expensive": share(sum(a["too_expensive"] <= p for a in answers), n)} for p in grid]
    return {"answers": n, "points": curve}


def summary(rnd, weights):
    """`aggregate`'s result for one round (without the corrected figure, which needs the project's grounding)."""
    rows = rnd.rows()
    return {
        "round": rnd.described(),
        "missing": rnd.missing(),
        "buy_share": buy_share(rows, weights),
        "pass_reasons": pass_reasons(rows),
        "buy_reasons": buy_reasons(rows),
        "buyer_types": buyer_types(rows, weights),
        "price": price_range(rows),
        "rows": rows,
    }
