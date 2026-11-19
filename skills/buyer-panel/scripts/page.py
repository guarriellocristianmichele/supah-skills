"""The round's page: its data and a self-contained HTML page drawn from it (RUN.md, the page step). Stdlib only."""
import html
import json
import os

from checks import LABELS
from ground import corrected_figure
from records import NOTHING, OFFER, PRICE_ANSWERS, panel_of, read_json
from tally import pct, price_curves, summary


def simulated_line(buyers, model):
    """The report's first line (SKILL.md, rule 1), for the page too."""
    return (f"Simulated panel: {buyers} synthetic buyers written by {model}, not real people. "
            "Every number below is a hypothesis to test on people.")


def verdict_of(result):
    """What `checks` prints under its table, from its result: the verdict line, the advisory checks that warned
    (by label) and why buyer types are descriptive. None of them in an older or hand-made checks file."""
    warned = result.get("warned") if isinstance(result.get("warned"), list) else []
    segments = result.get("segments") if isinstance(result.get("segments"), dict) else {}
    line = result.get("verdict_line")
    return {"line": line if isinstance(line, str) else None, "advisory": result.get("advisory") is True,
            "warned": [LABELS.get(n, str(n)) for n in warned],
            "buyer_types": segments.get("why") if isinstance(segments.get("why"), str) else None}


def page_data(rnd, weights):
    result = summary(rnd, weights)
    rows = result.pop("rows")
    corrected = corrected_figure(rnd, rows, weights)
    if corrected:
        result["corrected"] = corrected
    # Checks may come from a summary.json written by a later step, or from `panel.py checks --out`; both optional.
    source = read_json(os.path.join(rnd.dir, "summary.json")) or {}
    if source.get("checks") is None:
        source = read_json(os.path.join(rnd.dir, "checks.json")) or {}
    checks = source.get("checks")
    brief = read_json(os.path.join(panel_of(rnd.dir), "brief.json")) or {}
    segments = []
    for r in rows:
        if r["segment"] not in segments:
            segments.append(r["segment"])
    return {
        "simulated": simulated_line(len(rnd.buyers), rnd.meta["model"]),
        "idea": brief.get("idea") if isinstance(brief.get("idea"), str) else rnd.meta["offer"],
        "round": result.pop("round"),
        "summary": result,
        "checks": checks,
        "verdict": verdict_of(source),
        "filters": {"segment": segments,
                    "decision": [d for d in ("BUY", "PASS") if any(r["decision"] == d for r in rows)],
                    "reason": sorted({r["reason"] for r in rows})},
        "chart": price_curves(rows),
        "rows": rows,
    }


PAGE_CSS = """
:root {
  --bg: #f3f2ef; --surface: #fbfaf8; --text: #23221f; --muted: #57554f; --line: #d3d0c9;
  --buy: #2d6a39; --pass: #8b3a28; --note-bg: #fbf1d9; --note-line: #9a7414; --warn: #6e520b;
  --too-cheap: #1d6b87; --cheap: #4f8f33; --expensive: #a8661a; --too-expensive: #a23a3a; --band: #e3e9df;
  --radius: 6px; --gap: 1rem;
  color-scheme: light dark;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #1a1b1d; --surface: #222326; --text: #e9e7e2; --muted: #aeaba4; --line: #3b3c40;
    --buy: #86c78f; --pass: #e79a86; --note-bg: #3a3220; --note-line: #d9b35a; --warn: #e2c06e;
    --too-cheap: #6cc0dd; --cheap: #9bd27f; --expensive: #e3a65c; --too-expensive: #ec8b8b; --band: #2c3a2c;
  }
}
:root[data-theme="dark"] {
  --bg: #1a1b1d; --surface: #222326; --text: #e9e7e2; --muted: #aeaba4; --line: #3b3c40;
  --buy: #86c78f; --pass: #e79a86; --note-bg: #3a3220; --note-line: #d9b35a; --warn: #e2c06e;
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
.warned { color: var(--warn); font-weight: 600; }
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
            if passed is False and value.get("advisory") is True:
                passed = "warn"                     # stated, never part of the verdict (READING.md, the checks)
            skip = {"name", "check", "id", "passed", "ok", "failed", "status", "advisory"}
            detail = ", ".join(f"{k} {json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v}"
                               for k, v in value.items() if k not in skip)
        else:
            detail = str(value)
        items.append((str(name), passed, detail))
    return items


STATUS = {True: ' <span class="passed">passed</span>', False: ' <span class="failed">failed</span>',
          "warn": ' <span class="warned">warn</span>', None: ""}


def checks_html(checks, verdict=None):
    """The Checks section as `checks` prints it: the verdict line, one item per check, the advisory warnings
    and the line on buyer types."""
    items = check_items(checks)
    if not items:
        return ""
    verdict = verdict or {}
    out = ['<section aria-labelledby="checks"><h2 id="checks">Checks</h2>']
    if verdict.get("line"):
        css = "warned" if verdict.get("advisory") else "failed"
        out.append(f'<p class="{css}" role="note">{esc(verdict["line"])}</p>')
    out.append('<ul class="checks">')
    for name, passed, detail in items:
        out.append(f"<li><strong>{esc(name)}</strong>{STATUS[passed]}{': ' + esc(detail) if detail else ''}</li>")
    out.append("</ul>")
    if verdict.get("warned"):
        out.append(f"<p>Advisory, not part of the verdict: {esc(', '.join(verdict['warned']))}.</p>")
    if verdict.get("buyer_types"):
        out.append(f'<p class="meta">{esc(verdict["buyer_types"])}</p>')
    out.append("</section>")
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
    ]
    c = s.get("corrected")
    if c:
        figure = "n/a" if c["figure"] is None else f"{pct(c['figure'])} {esc(c['measure'])}"
        summary.append(("Corrected", f"{figure}, discounted x {c['ratio']:g} from grounding {esc(c['grounding'])} "
                                     f"of panel {esc(c['panel'])} ({esc(c['test'])}, {c['acted']} of {c['reached']}, "
                                     f"{esc(c['date'])})"))
    summary += [
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
<p class="meta">Round {esc(rnd['label'])} at {money(rnd['price'], cur)}{' per ' + esc(rnd['period']) if rnd.get('period') else ''}. The card read: &ldquo;{esc(rnd['offer'])}&rdquo; Interviews: {esc(how)}. Model: {esc(rnd['model'])}.</p>
</header>
<section aria-labelledby="summary">
<h2 id="summary">Summary</h2>
<dl class="summary">
{"".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in summary)}
</dl>
</section>
{checks_html(data.get('checks'), data.get('verdict'))}
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
