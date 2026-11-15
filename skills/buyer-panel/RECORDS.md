# Records

The panel ledger's files and the schemas `panel.py validate` enforces. JSON objects in `.json` files, one JSON object per line in `.jsonl` files, UTF-8. Text fields are non-empty unless marked "may be empty"; numbers are 0 or more; fields not listed are allowed and ignored, so later modes can add their own.

## Layout

```text
.buyer-panel/<slug>/
  brief.json          the idea, audience, price and real alternatives
  research.md         one line per fact: what, source URL, date seen
  plan.json           segments with shares and budget ranges
  buyers.jsonl        the panel, written once, reused by every round
  history.md          one line per round
  real/<label>.json   what real people did in one real test (ground)
  grounding.jsonl     panel.py ground: real against predicted, one line per real test
  price-p<n>.md       a price run's report (PRICE.md)
  rounds/<label>/
    round.json        what this round showed and how it was run
    cards.jsonl       panel.py deal: each buyer's batch and option order
    answers/batch-<n>.jsonl   one worker's answers (or answers.jsonl inline)
    judge-input.jsonl panel.py reactions: what the judge may see
    scores.jsonl      the judge's output
    summary.json      panel.py aggregate --out
    checks.json       panel.py checks --out
    critique.md       the devil's advocate (CRITIQUE.md)
    diff.json         panel.py diff --out: this round against an earlier one (fix and later modes)
    compare.json      panel.py compare --out: variant A's folder only, the two halves side by side
    report.md         the round's report
    page.json         panel.py page: the page data
    page.html         panel.py page: the private page, self-contained
  test/               the real-test kit (TEST.md); an older kit moves to test-<written date>/
    test.json         the go and stop thresholds, written before the test runs
    interview.md      the Mom Test interview script
    landing.md        the smoke-test landing brief
```

Round labels are short and unique within the panel: `r1` for the first round; later modes name theirs (`price` uses `p<n>-<price>`, such as `p1-14`).

## brief.json

| field | type | what |
|---|---|---|
| `idea` | text | the idea in one line, as a stranger would describe it |
| `audience` | text | who would pay |
| `price` | number | the seller's price |
| `currency` | text | ISO code, `EUR` |
| `alternatives` | list | each `{name, price}` (plus any `note`): what the audience buys or uses instead, at real prices; `offer` and `nothing` are reserved names |

## plan.json

| field | type | what |
|---|---|---|
| `size` | whole number | buyers in the panel |
| `currency` | text | budgets' currency |
| `segments` | list | each `{name, share, budget: [low, high]}`, plus `source` (the `research.md` line it rests on); names distinct, shares above 0 adding up to 1, `low` <= `high` |

## buyers.jsonl

| field | type | what |
|---|---|---|
| `id` | text | unique in the panel: `b001`, `b002`... |
| `name` | text | a name someone in that segment and country could have |
| `segment` | text | one of the plan's segment names |
| `budget` | number | what this buyer can spend in the category per period, inside the segment's range |
| `currency` | text | |
| `habits` | text | how they work or live where the product would fit |
| `current_solution` | text | what they use now, `nothing` included |
| `last_spend` | number | what they last paid in the category |
| `objection` | text | one honest reason they might not buy anything new |

With `plan.json` in the same folder (or in the same `validate` call), each buyer's segment must be in the plan and the budget inside its range.

## round.json

| field | type | what |
|---|---|---|
| `label` | text | the round's folder name |
| `offer` | text | the offer as the card shows it |
| `price` | number | the price on the card |
| `currency` | text | |
| `options` | list | option ids shown: `offer`, `nothing` and the alternatives' names, distinct |
| `model` | text | the model that wrote the buyers' answers, with its version |
| `interviews` | `orchestrate` or `inline` | fresh contexts in batches, or one buyer at a time in one context |
| `batch_size` | whole number | buyers per interview context; 1 inline |
| `seed` | whole number | optional: `deal`'s seed, so the option orders can be dealt again |
| `base` | text | optional: the round this one is compared with (`fix`) |
| `fix` | tag | optional: the pass reason this round's change answers |
| `change` | text | optional: the change to the base offer, in one line |
| `screen` | `true` | optional: shown only to the buyers who gave the reason |
| `screened_in` | text | optional: the screening round the change won |
| `variant` | `A` or `B` | optional: the variant this half of the panel saw (`compare`) |
| `compare` | text | optional: the other variant's round label |
| `competitor` | object | optional: `{name, price}` of the competitor this round added, plus `was` (its price in the base round) when it was repriced; `name` is one of `options`, never `offer` or `nothing` (`competitor`) |

## answers

`answers.jsonl` or `answers/*.jsonl` in the round folder; all files count as one round, and a buyer may appear once.

| field | type | what |
|---|---|---|
| `buyer_id` | text | a buyer of the panel |
| `round` | text | the round's label |
| `options` | list | the option ids in the order this buyer saw them: the round's options, reordered |
| `reaction` | text | the free reaction, written before the choice |
| `choice` | text | one of `options` |
| `give_up` | text, may be empty | what the buyer gives up to pay; required when `choice` is `offer` |
| `price` | object | `{too_cheap, cheap, expensive, too_expensive}`, four numbers in the card's currency |

Price answers out of order (each must be below the next) are kept in the file, then dropped from the price range and counted by `aggregate`.

## scores.jsonl

| field | type | what |
|---|---|---|
| `buyer_id` | text | |
| `round` | text | |
| `intent` | 1 to 5 | the anchor statement closest to the reaction (SCORING.md) |
| `reason` | tag | the main reason, lowercase words joined by hyphens: `already-paid` |
| `quote` | text | the words that carry the reason, copied from the reaction (case and spacing aside) |

## test.json

The thresholds that decide the real test, written by `test` before anything goes live and never edited after; a new kit gets a new file.

| field | type | what |
|---|---|---|
| `round` | text | the round the kit was built from |
| `written` | date | `YYYY-MM-DD`, the day the thresholds were set |
| `ends` | date | `YYYY-MM-DD`, the last day of the test; not before `written` |
| `offer` | text | the offer the test shows |
| `price` | number | the price the test shows |
| `currency` | text | |
| `objections` | list | the reason tags the interviews probe, at least one |
| `sample` | object | `visits` and `interviews`, whole numbers above 0: the planned base of each share; each base a metric uses is required |
| `thresholds` | object | one or more of `signups` and `preorders` (shares of visits) and `commitments` (share of interviews that end in a commitment), each `{go, stop}`: shares from 0 to 1, `stop` below `go` |

Reading a result against it: a metric's share is its count over its base (sign-ups or pre-orders over visits, commitments over interviews). Read it once the base reaches the sample or `ends` has passed; a base still short of the sample on `ends` is reported as short, not decided. At or above `go` is go, at or below `stop` is stop, in between is unclear. The test as a whole is stop when any metric is stop, go when every metric is go, and unclear otherwise.

## diff.json

Written by `panel.py diff ROUND_A ROUND_B --out FILE`, never by hand. Both rounds must use the same `buyers.jsonl`; only buyers answered and scored in both are compared.

| field | what |
|---|---|
| `before`, `after` | each round's label, offer, price, currency, model, interviews, batch size |
| `buyers` | `both` (how many compared), `only_before`, `only_after` (ids left out) |
| `flips` | `pass_to_buy`, `buy_to_pass`: buyer ids |
| `switches` | each `{buyer_id, from, to}`: every change of option, between competitors too |
| `choices` | each `{option, before, after}`: buyers per option, ROUND_A's options first, then any new in ROUND_B |
| `buy_share` | `before` and `after` (buyers, buy, raw, discounted), `raw_change`, `discounted_change`, `scheme` |
| `intent` | mean `before`, `after` and `change`; `up` and `down` (ids), `same` (a count) |
| `pass_reasons`, `buy_reasons` | `before` and `after` top five with counts; `new` and `gone` tags |
| `price` | `card` (before, after, change, currency), each round's price range, `range_change`, `optimal_change`, `indifference_change` |
| `rows` | per buyer: id, name, segment, `change` (`pass-to-buy`, `buy-to-pass`, `switch`, `same`) and `before`, `after` (choice, decision, intent, reason, quote, give-up, price answers) |
| `competitor` | only from `panel.py competitor`: `name`, `change` (`added` or `repriced`), `price` (before, after), `chosen` (buyers before, after), `switched_to` (each `{buyer_id, from, reason, quote}`), `left` (each `{buyer_id, to, reason, quote}`), `other_switches` (switches between other options), `stayed` (each `{option, buyers, reasons}`: who kept their choice and the reasons, with counts, that held them in ROUND_B) |

## compare.json

Written by `panel.py compare ROUND_A ROUND_B --out FILE`, never by hand. The two rounds are halves of one panel: a buyer answered in both is refused.

| field | what |
|---|---|
| `a`, `b` | each half: label, variant, offer, price, currency, `buyers`, `buy`, `raw`, `discounted`, `choices` (each `{option, count}`), `pass_reasons`, `buy_reasons`, `price_range`, `segments` (buyers per segment), `missing` (dealt a card in its `cards.jsonl` with no scored answer; null without that file) |
| `scheme` | the intent weights' name |
| `difference` | B minus A: `raw` and `discounted`, from the counts |
| `noise` | `standard_error`: of the raw difference, from the two halves pooled; `one_buyer`: what one buyer moves the smaller half. Shown beside the difference, never tested against it |
| `segments`, `balanced` | buyers per segment in each half; `balanced` is false when a segment differs by more than one buyer |

## Real results

`real/<label>.json`: what real people did in one real test, from the user's records.

| field | type | what |
|---|---|---|
| `label` | text | short and unique in the panel: `smoke-1`, `talks-1` |
| `test` | `smoke-test`, `interviews` or `pre-sale` | which real test was run |
| `round` | text | the label of the round that showed the offer tested, at the price tested |
| `date` | `YYYY-MM-DD` | when the test ended |
| `source` | text | where the numbers come from: analytics export, interview notes, payment records |
| `price` | number | the price the test charged or asked; must equal the round's |
| `currency` | text | must equal the round's |

Then the two counts of its test, whole numbers, the second no larger than the first:

| `test` | people reached (1 or more) | people who acted | the rate measures |
|---|---|---|---|
| `smoke-test` | `visits` | `conversions` | conversions per visit |
| `interviews` | `interviews` | `commitments` (a deposit, a letter of intent, a start date) | commitments per interview |
| `pre-sale` | `asked` | `paid` | payments per person asked |

## grounding.jsonl

Written by `panel.py ground`, one line per real test, read by `aggregate`. Do not write it by hand.

| field | what |
|---|---|
| `label`, `test`, `round`, `date`, `source` | copied from the real-results file |
| `offer`, `price`, `currency` | the round's, as its card showed them |
| `real` | `{reached, acted, rate, measure}`: the two counts, their ratio to 4 places, and what it measures |
| `predicted` | `{buyers, buy, raw, discounted, weights}`: the round's BUY share as `aggregate` gives it, with the weights used |
| `ratio` | the real rate divided by the round's discounted share, to 4 places |

`aggregate` applies the line with the latest `date` (on a tie, the one written later): its `corrected` field holds `figure` (the round's discounted share times `ratio`, to 4 places), `ratio`, `grounding` (the label), `test`, `round`, `date`, `reached`, `acted` and `measure`. A round aggregated with weights other than the grounding's gets `figure: null` and a `problem` saying why. Without `grounding.jsonl` there is no `corrected` field.

## Exit codes

`0` done; `1` a panel check failed (`checks`; READING.md); `2` bad arguments; `3` invalid records: the output lists file, line, field and problem, and nothing is computed from them.
