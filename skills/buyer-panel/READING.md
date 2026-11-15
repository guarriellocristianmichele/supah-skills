# Reading a panel

How to turn `aggregate`'s numbers into a report that says what they can and cannot carry.

## What each number means

- **Raw BUY share**: the buyers who chose the offer over the real alternatives and `nothing`. It is stated intent, and people overstate it too.
- **Discounted BUY share**: the raw buyers weighted by how firmly they said it (SCORING.md). Quote it as "about N in 100 might buy", never as a conversion rate.
- **Reasons**: the tags with counts. The top pass reason is what to fix first or test first; one buyer's reason is an anecdote.
- **Buyer types**: segments ranked by discounted share. They say whom to talk to first. Synthetic panels flatten and invent group differences (in Bisbee et al., 32% of the coefficients that differed from humans flipped sign), so a split between types is descriptive: never write "segment A prefers X" as a finding, and never draw strategy from it.
- **Price range**: Van Westendorp's acceptable range, with the optimal and indifference points, from the answers in order. LLM buyers state willingness to pay two to three times too high (Brand et al.): the range is an upper bound, and the dropped count shows how many answers made no sense.
- **Missing**: buyers left out because an answer or a score is missing. `aggregate` prints a `Missing` line for them, and the verdict names how many.

## The checks

`panel.py checks` runs five checks on the answered and judged buyers of a round and exits 1 when any fails. Each catches one way a synthetic panel misleads (research note, `docs/research/2026-11-synthetic-panels.md` in the supah-skills repository). The research measured these failures; it set no cutoffs. Every threshold below is this skill's judgement, built from those measurements. Changing one is a reviewed change with a reason (ADR 0014), never an edit to rescue a round.

| check | fails when | evidence | why this threshold |
|---|---|---|---|
| `spread` | the standard deviation of judged intent is under 0.8 | Bisbee et al.: synthetic answers had a standard deviation of 16.1 against 31.4 for people, about half; Maier et al.: models asked for 1 to 5 answered mostly 3 | five anchors used evenly give 1.41, and half of that, the shrink Bisbee measured, is about 0.7. Under 0.8, most buyers sit on one or two neighbouring anchors |
| `similarity` | the mean overlap of content words between two reactions (Jaccard, function words left out) is over 0.5 | Wang, Morgenstern and Dickerson: models flatten groups, and reached human word diversity only at a temperature where text broke down; BenchForm: models conform to answers they can see | different people reacting on their own share few content words (the normal test round: 0.01). Half their words in common, on average, means one voice repeated or a batch that saw another's answers |
| `praise` | praise words (amazing, love, perfect... in English and Italian) pass 2 per 100 words of reaction | Sharma et al.: feedback warms when the model knows the user wrote or likes the work | the card hides the owner, so a buyer has no one to please. Praise says nothing about buying (the judge ignores tone), and more than one word in fifty means the framing leaked or the model is flattering. Reactions in other languages are not covered and read low |
| `buy_share` | the raw share choosing the offer is over 0.5 | Sun and Morwitz: 15.3% of households said they would buy a computer and 5.7% did; Chen 2026: simulated customers push real non-buyers toward purchase | more than half the panel picking an unknown seller's new product over what they already pay for and over buying nothing is far above stated intent among people. It can happen, but it has to be shown on people before anyone believes it |
| `order` | the share choosing whatever their card listed first is at least twice chance (chance is 1 over the number of options) | Dominguez-Olmedo et al.: survey answers driven by option position; Brand et al.: GPT gravitates toward the first option | `deal` shuffles every card, so each option leads equally often. Twice chance (50 of 100 against 25 with four options) is far beyond what shuffling gives by luck; this is a warning line, not a significance test |

A check with fewer than two judged buyers reads `n/a` and fails. The checks catch these failures in the text; they cannot prove a round that passes is right.

**When a check fails.** The round's verdict is the line `checks` printed, `Do not trust this round: <checks> failed.`, unchanged: it replaces both verdicts below. Under it, name the likely cause and the change before running the round again:

- `spread`, `similarity`: buyers too alike (rewrite them per BUYERS.md with more varied habits and objections), or batches that leaked (smaller batches, fresh contexts).
- `praise`, `buy_share`: a card that says who is asking, praises the offer or prices it apart from the alternatives (rewrite it per INTERVIEW.md); then the judge's tags and intents.
- `order`: workers that ignored the order `deal` recorded (compare `options` in the answers with `cards.jsonl`), or cards with one option styled to win.

**Buyer types.** `checks` also prints the line that marks buyer types as descriptive, with its reason: copy it under the checks table so no reader takes a split between types as a finding.

## The report

```text
Simulated panel: <N> synthetic buyers written by <model>, not real people. Every number below is a hypothesis to test on people.

# <idea in one line>, round <label>

## Summary
<aggregate's summary lines, unchanged>

## Buyers
<aggregate's buyer table, unchanged>

## Checks
<checks' table and its buyer-types line, unchanged>

## How this panel was run
<size and segments with their sources; interviews: orchestrate batches of <batch_size> in fresh contexts, or inline (independence partial: one context saw every buyer in turn); judge and devil's advocate each in its own context, or not; weights scheme; the research date; what was assumed, not sourced; whether ai-slop-prose swept this report>

## Devil's advocate
<critique.md, unchanged: the strongest case against the idea, written in its own context (CRITIQUE.md)>

## Verdict
<with a failed check: checks' verdict line, the likely cause and the change to make. Otherwise one of the two verdicts below, with the two or three numbers and reasons that decided it, and what the devil's advocate raised that the panel could not answer>

## First real test this week
<one test, its cost, and the result that would change the verdict>
```

## The verdict

These two verdicts apply only to a round that passed every check.

- **Worth testing on real people**: some buyers chose the offer over the real alternatives, their reasons concern what the offer does (not only that it is cheap), and the top pass reason is something a real test can probe.
- **Not yet**: almost nobody chose it, or the buyers who did gave reasons a real buyer would not pay for, or the top pass reason is no need at all; name what would have to change before a test is worth running.

Neither verdict says the idea will or will not sell.

## The first real test

Pick one, from the top pass reason and the most likely buyer type (research note, "Cheap real-world validation to end with"):

- **Five interviews** with people of the most likely type, about their last purchase in the category and what they paid, never about the idea (the Mom Test): when the top reason is unclear or about need.
- **A smoke test**: a one-page offer at the panel's price with one action to measure (a sign-up or a deposit), shared where that type already gathers: when the reasons are clear and the question is whether anyone acts.
- **A pre-sale**: ask three people of the most likely type for a deposit or a signed letter of intent: when the panel says the offer is wanted and the price is the doubt.

State the threshold that would change the verdict before the test runs.
