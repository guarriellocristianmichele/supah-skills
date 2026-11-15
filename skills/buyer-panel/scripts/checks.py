"""Checks that flag a round not to be trusted (READING.md, "The checks"), and buyers too alike to interview
(BUYERS.md, "The variety check"): each threshold with its source and its reason. Stdlib only."""
import re

from records import OFFER, normalise

MIN_SPREAD = 0.8
MAX_TOP_REASON = 0.6      # share of buyers giving the most common reason tag
MAX_OVERLAP = 0.5         # mean word overlap between two reactions
MAX_PRAISE = 2.0          # praise words per 100 words of reaction
MAX_BUY_SHARE = 0.5       # raw share choosing the offer
MAX_FIRST_TIMES_CHANCE = 2  # the option shown first, chosen this many times as often as chance gives
WORD = re.compile(r"[^\W\d_]+(?:['’-][^\W\d_]+)*")
# function words left out of the overlap, so two reactions are alike for what they say, not for "the" and "I"
STOP_WORDS = frozenset("""
a an and are as at be but by do for from had has have i i'm i'd i'll if in is it it's its me my no not of on or
our so than that the their them then there they this to too was we were what when which who will with would you
your il lo la i gli le un una e o ma di da in con su per che non mi ci si è
""".split())
# praise that says how good the product is, not what it does; English and Italian forms
PRAISE_WORDS = frozenset("""
amazing awesome beautiful brilliant delightful excellent exceptional fabulous fantastic flawless game-changer
genius gorgeous great impressive incredible love loved lovely loving magnificent marvellous marvelous must-have
outstanding perfect perfectly phenomenal remarkable revolutionary spectacular stunning superb terrific wonderful
bellissimo bellissima eccezionale fantastico fantastica fantastici geniale incredibile magnifico magnifica
meraviglioso meravigliosa ottimo ottima perfetto perfetta perfetti stupendo stupenda
""".split())
LABELS = {"spread": "intent spread", "similarity": "reason similarity", "overlap": "reaction overlap",
          "praise": "praise words",
          "buy_share": "BUY share", "order": "first-option choice"}
SEGMENTS = {"descriptive_only": True,
            "why": "Buyer types are descriptive, not findings: synthetic panels flatten and misportray groups "
                   "(Wang, Morgenstern and Dickerson), and in Bisbee et al. 32% of the coefficients that differed "
                   "from humans flipped sign."}


def words(text):
    return WORD.findall(text.lower())


def top_reason(rows):
    """(share of buyers giving the most common reason tag, that tag); on a tie the first tag in name order."""
    if len(rows) < 2:
        return None, None
    counts = {}
    for r in rows:
        counts[r["reason"]] = counts.get(r["reason"], 0) + 1
    tag = min(counts, key=lambda t: (-counts[t], t))
    return round(counts[tag] / len(rows), 3), tag


def overlap(texts):
    """Mean overlap (Jaccard) of the content words of every pair of reactions."""
    sets = [set(words(t)) - STOP_WORDS for t in texts]
    pairs = [(a, b) for i, a in enumerate(sets) for b in sets[i + 1:]]
    if not pairs:
        return None
    return round(sum(len(a & b) / len(a | b) if a | b else 1 for a, b in pairs) / len(pairs), 3)


def praise(texts):
    """Praise words per 100 words of reaction, across the round."""
    found = [w for t in texts for w in words(t)]
    if not found:
        return None
    return round(sum(w in PRAISE_WORDS for w in found) / len(found) * 100, 1)


def first_option_share(rows):
    """(share of buyers choosing the option shown first, the share chance alone gives)."""
    if not rows:
        return None, None
    first = sum(r["options"][0] == r["choice"] for r in rows) / len(rows)
    chance = sum(1 / len(r["options"]) for r in rows) / len(rows)
    return round(first, 3), round(chance, 3)


def spread(rows):
    """Population standard deviation of the judged intent."""
    intents = [r["intent"] for r in rows]
    if len(intents) < 2:
        return None
    mean = sum(intents) / len(intents)
    return round((sum((x - mean) ** 2 for x in intents) / len(intents)) ** 0.5, 3)


def check(name, what, value, threshold, passed):
    return {"name": name, "what": what, "value": value, "threshold": threshold,
            "passed": value is not None and passed(value)}


def run_checks(rnd):
    rows = rnd.rows()
    reactions = [rnd.answers[r["buyer_id"]]["reaction"] for r in rows]
    top_share, tag = top_reason(rows)
    found = [
        check("spread", "standard deviation of intent", spread(rows), f">= {MIN_SPREAD:g}",
              lambda v: v >= MIN_SPREAD),
        dict(check("similarity", "share of buyers giving the most common reason tag", top_share,
                   f"<= {MAX_TOP_REASON:g}", lambda v: v <= MAX_TOP_REASON), reason=tag),
        check("overlap", "mean word overlap between two reactions", overlap(reactions),
              f"<= {MAX_OVERLAP:g}", lambda v: v <= MAX_OVERLAP),
        check("praise", "praise words per 100 words of reaction", praise(reactions), f"<= {MAX_PRAISE:g}",
              lambda v: v <= MAX_PRAISE),
        check("buy_share", "raw share choosing the offer",
              round(sum(r["choice"] == OFFER for r in rows) / len(rows), 3) if rows else None,
              f"<= {MAX_BUY_SHARE:g}", lambda v: v <= MAX_BUY_SHARE),
    ]
    first, chance = first_option_share(rows)
    bound = None if chance is None else round(MAX_FIRST_TIMES_CHANCE * chance, 3)
    found.append(dict(check("order", "share choosing the option shown first", first,
                            f"< {MAX_FIRST_TIMES_CHANCE:g} x chance ({bound})", lambda v: v < bound),
                      chance=chance))
    failed = [c["name"] for c in found if not c["passed"]]
    verdict = f"Do not trust this round: {', '.join(LABELS[n] for n in failed)} failed." if failed else None
    return {"buyers": len(rows), "checks": found, "failed": failed, "verdict_line": verdict, "segments": SEGMENTS}


# ---------------------------------------------------------------- buyer variety

SHARE_TOLERANCE = 0.05    # a segment's share may miss the plan by this much, or by one buyer when that is more
MIN_BUDGET_SPAN = 0.5     # a segment's budgets cover at least this part of its planned range
MIN_SPAN_BUYERS = 3       # segments smaller than this are not measured for spread
VARIETY_LABELS = {"count": "buyer count", "shares": "segment shares", "budget_spread": "budget spread",
                  "names": "duplicate names", "objections": "duplicate objections"}


def repeated(buyers, field):
    """Ids of the buyers whose `field` another buyer repeats, case and spacing aside."""
    seen = {}
    for b in buyers:
        seen.setdefault(normalise(b[field]), []).append(b["id"])
    return sorted(i for ids in seen.values() if len(ids) > 1 for i in ids)


def narrowest_span(buyers, plan):
    """The smallest part of a segment's planned budget range its buyers cover; None when no segment is measured."""
    spans = []
    for seg in plan["segments"]:
        budgets = [b["budget"] for b in buyers if b["segment"] == seg["name"]]
        low, high = seg["budget"]
        if len(budgets) >= MIN_SPAN_BUYERS and high > low:
            spans.append((max(budgets) - min(budgets)) / (high - low))
    return round(min(spans), 3) if spans else None


def run_variety(buyers, plan):
    """The buyers before any interview: the count and shares the plan set, budgets spread across each segment's
    range, and no name or objection written twice."""
    n, size = len(buyers), plan["size"]
    tolerance = max(SHARE_TOLERANCE, 1 / size)
    gap = max(abs(sum(b["segment"] == seg["name"] for b in buyers) / n - seg["share"])
              for seg in plan["segments"]) if n else None
    span = narrowest_span(buyers, plan)
    names, objections = repeated(buyers, "name"), repeated(buyers, "objection")
    spread_check = check("budget_spread", f"narrowest part of a segment's budget range its buyers cover "
                                          f"(segments of {MIN_SPAN_BUYERS} or more buyers)",
                         span, f">= {MIN_BUDGET_SPAN:g}", lambda v: v >= MIN_BUDGET_SPAN)
    found = [
        check("count", "buyers against the plan's size", n, f"= {size}", lambda v: v == size),
        check("shares", "widest gap between a segment's share and the plan's", None if gap is None else round(gap, 3),
              f"<= {round(tolerance, 3):g}", lambda v: v <= tolerance + 1e-9),
        dict(spread_check, passed=span is None or spread_check["passed"]),     # no segment large enough: not measured
        dict(check("names", "buyers sharing a name", len(names), "= 0", lambda v: v == 0), buyers=names),
        dict(check("objections", "buyers sharing an objection word for word", len(objections), "= 0",
                   lambda v: v == 0), buyers=objections),
    ]
    failed = [c["name"] for c in found if not c["passed"]]
    verdict = (f"Rewrite the buyers before any interview: {', '.join(VARIETY_LABELS[x] for x in failed)} failed."
               if failed else None)
    return {"buyers": n, "checks": found, "failed": failed, "verdict_line": verdict}
