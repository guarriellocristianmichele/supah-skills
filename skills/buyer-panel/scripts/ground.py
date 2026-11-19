"""Real results against the panel's prediction, stored for the whole project, and the corrected figure every later
round of any panel in the project shows (GROUND.md). Stdlib only."""
import os

from records import REAL_TESTS, RecordErrors, load, load_round, panel_of, problem, project_of, write_jsonl
from tally import discounted_count, summary


def ground(path, panel, weights):
    """Compare one real-results file with the round it tested and store the ratio; returns the grounding line."""
    rec = load(path, "real", "a real/<label>.json file")["data"]
    panel = panel or os.path.join(os.path.dirname(os.path.abspath(path)), os.pardir)
    round_dir = os.path.join(panel, "rounds", rec["round"])
    if not os.path.isdir(round_dir):
        raise RecordErrors([problem(path, 0, "round", f"no round {rec['round']} in {panel}")])
    rnd = load_round(round_dir)
    meta = rnd.meta
    for field in ("price", "currency"):
        if rec[field] != meta[field]:
            raise RecordErrors([problem(path, 0, field, (
                f"the real test used {rec[field]}, round {rec['round']} showed {meta[field]}: "
                "ground against a round with the offer and price tested"))])
    result = summary(rnd, weights)
    expected = discounted_count(result["rows"], weights)
    if not expected:
        raise RecordErrors([problem(path, 0, "round", (
            f"round {rec['round']} predicts no buyer, so there is nothing to compare the real result with"))])
    reached_field, acted_field, measure = REAL_TESTS[rec["test"]]
    reached, acted = rec[reached_field], rec[acted_field]
    s = result["buy_share"]
    grounding = {
        "panel": os.path.basename(os.path.normpath(os.path.abspath(panel))), "label": rec["label"],
        "test": rec["test"], "round": rec["round"], "date": rec["date"], "source": rec["source"],
        "offer": meta["offer"], "price": meta["price"], "currency": meta["currency"], "period": meta.get("period"),
        "real": {"reached": reached, "acted": acted, "rate": round(acted / reached, 4), "measure": measure},
        "predicted": {"buyers": s["buyers"], "buy": s["buy"], "raw": s["raw"], "discounted": s["discounted"],
                      "weights": weights},
        "ratio": round((acted / reached) / (expected / s["buyers"]), 4),
    }
    ledger = os.path.join(project_of(panel), "grounding.jsonl")
    kept = load(ledger, "grounding", "a grounding.jsonl file")["data"] if os.path.exists(ledger) else []

    def same(g):
        return (g["panel"], g["label"]) == (grounding["panel"], grounding["label"])

    if any(same(g) for g in kept):
        kept = [grounding if same(g) else g for g in kept]
    else:
        kept.append(grounding)
    write_jsonl(ledger, kept)
    return grounding


def latest_grounding(round_dir):
    """The project's grounding line with the latest test date, from any of its panels (a tie goes to the line
    written later), or None."""
    ledger = os.path.join(project_of(panel_of(round_dir)), "grounding.jsonl")
    if not os.path.exists(ledger):
        return None
    latest = None
    for g in load(ledger, "grounding", "a grounding.jsonl file")["data"]:
        if latest is None or g["date"] >= latest["date"]:
            latest = g
    return latest


def corrected_figure(rnd, rows, weights):
    """The latest grounding applied to these rows of the round, or None without one. A ratio measured on a round
    priced per one period (a month) says nothing of buyers paying per another (a booking): no figure then."""
    latest = latest_grounding(rnd.dir)
    if latest is None:
        return None
    m = latest["real"]
    out = {"figure": None, "ratio": latest["ratio"], "panel": latest["panel"], "grounding": latest["label"],
           "test": latest["test"], "round": latest["round"], "date": latest["date"], "reached": m["reached"],
           "acted": m["acted"], "measure": m["measure"]}
    grounded_on = latest["predicted"]["weights"]
    period = rnd.meta.get("period")
    if grounded_on["by_intent"] != weights["by_intent"]:
        out["problem"] = (f"the ratio was computed on {grounded_on.get('scheme', 'other weights')}, "
                          f"this round uses {weights['scheme']}")
    elif latest.get("period") != period:
        def per(p):
            return f"priced per {p}" if p else "priced with no period stated"

        out["problem"] = (f"the ratio was measured on a round {per(latest.get('period'))}, "
                          f"this round is {per(period)}")
    elif rows:
        out["figure"] = round(latest["ratio"] * discounted_count(rows, weights) / len(rows), 4)
    return out
