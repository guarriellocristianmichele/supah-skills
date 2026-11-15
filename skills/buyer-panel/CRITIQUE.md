# Devil's advocate

After the numbers and the checks, one separate voice argues the strongest case against the idea. Telling simulated respondents to play devil's advocate has no measured effect, and it would push every buyer the same way (research note, "Sycophancy and what reduces it"). So the critique runs once, after the panel, in a context that has seen no interview, and it stays out of every buyer's answer.

## What the critic reads

`brief.json`, `research.md`, the round's `summary.json` and `checks.json`, this file's brief, and nothing else: no worker brief, no cards, no answers files, and nothing about who is asking or what they hope. It writes `P/rounds/<label>/critique.md` and nothing else.

## Critic brief

> You are reviewing another company's product idea for an investor who has to decide whether it deserves a real test. Argue the strongest case against it: the case a smart, informed sceptic would make, not a list of every possible risk. Cover, in this order:
>
> 1. **Why the buyers who matter will not switch**: what the alternatives in `research.md` already do for them, and what switching costs them.
> 2. **The way it most likely fails**: the one mechanism (reaching buyers, willingness to pay, trust, a habit, a competitor's response) that kills it first, and why that one.
> 3. **What the panel cannot see**: where the summary's numbers are likely too kind (synthetic buyers overstate what they would pay, and differences between buyer types are not findings), and what a failed check, if any, means for this idea.
> 4. **What would prove this critique wrong**: one observable result from real people that would settle it.
>
> Base every fact on a line of `research.md` or a number in `summary.json` and say which; mark anything else as your reasoning. Never write as a buyer, never quote a reaction as if it were yours, never invent a buyer or a statistic. At most 250 words, plain prose, no headings beyond the four bold labels.

## Rules

- The critique is a report section of its own, `## Devil's advocate`, copied from `critique.md` unchanged. It never goes into `answers`, `scores`, a quote, a reason count or the buyer table, and no later round shows it to a buyer or to the judge.
- It does not change a number or the checks. The verdict may name what it raised that the panel could not answer; it is not a vote.
- Without a subagent tool, write it yourself after `checks.json` exists, reading only the files above, and say in the method section that the critique did not run in its own context.
