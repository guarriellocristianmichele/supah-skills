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
  rounds/<label>/
    round.json        what this round showed and how it was run
    cards.jsonl       panel.py deal: each buyer's batch and option order
    answers/batch-<n>.jsonl   one worker's answers (or answers.jsonl inline)
    judge-input.jsonl panel.py reactions: what the judge may see
    scores.jsonl      the judge's output
    summary.json      panel.py aggregate --out
    report.md         the round's report
```

Round labels are short and unique within the panel: `r1` for the first round; later modes name theirs.

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

`0` done; `1` reserved for a failed panel check; `2` bad arguments; `3` invalid records: the output lists file, line, field and problem, and nothing is computed from them.
