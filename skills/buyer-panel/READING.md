# Reading a panel

How to turn `aggregate`'s numbers into a report that says what they can and cannot carry.

## What each number means

- **Raw BUY share**: the buyers who chose the offer over the real alternatives and `nothing`. It is stated intent, and people overstate it too.
- **Discounted BUY share**: the raw buyers weighted by how firmly they said it (SCORING.md). Quote it as "about N in 100 might buy", never as a conversion rate.
- **Reasons**: the tags with counts. The top pass reason is what to fix first or test first; one buyer's reason is an anecdote.
- **Buyer types**: segments ranked by discounted share. They say whom to talk to first. Synthetic panels flatten and invent group differences (in Bisbee et al., 32% of the coefficients that differed from humans flipped sign), so a split between types is descriptive: never write "segment A prefers X" as a finding, and never draw strategy from it.
- **Price range**: Van Westendorp's acceptable range, with the optimal and indifference points, from the answers in order. LLM buyers state willingness to pay two to three times too high (Brand et al.): the range is an upper bound, and the dropped count shows how many answers made no sense.
- **Missing**: buyers left out because an answer or a score is missing. `aggregate` prints a `Missing` line for them, and the verdict names how many.

## The report

```text
Simulated panel: <N> synthetic buyers written by <model>, not real people. Every number below is a hypothesis to test on people.

# <idea in one line>, round <label>

## Summary
<aggregate's summary lines, unchanged>

## Buyers
<aggregate's buyer table, unchanged>

## How this panel was run
<size and segments with their sources; interviews: orchestrate batches of <batch_size> in fresh contexts, or inline (independence partial: one context saw every buyer in turn); judge in its own context; weights scheme; the research date; what was assumed, not sourced; whether ai-slop-prose swept this report>

## Verdict
<one of the two verdicts below, with the two or three numbers and reasons that decided it>

## First real test this week
<one test, its cost, and the result that would change the verdict>
```

## The verdict

- **Worth testing on real people**: some buyers chose the offer over the real alternatives, their reasons concern what the offer does (not only that it is cheap), and the top pass reason is something a real test can probe.
- **Not yet**: almost nobody chose it, or the buyers who did gave reasons a real buyer would not pay for, or the top pass reason is no need at all; name what would have to change before a test is worth running.

Neither verdict says the idea will or will not sell.

## The first real test

Pick one, from the top pass reason and the most likely buyer type (research note, "Cheap real-world validation to end with"):

- **Five interviews** with people of the most likely type, about their last purchase in the category and what they paid, never about the idea (the Mom Test): when the top reason is unclear or about need.
- **A smoke test**: a one-page offer at the panel's price with one action to measure (a sign-up or a deposit), shared where that type already gathers: when the reasons are clear and the question is whether anyone acts.
- **A pre-sale**: ask three people of the most likely type for a deposit or a signed letter of intent: when the panel says the offer is wanted and the price is the doubt.

State the threshold that would change the verdict before the test runs.
