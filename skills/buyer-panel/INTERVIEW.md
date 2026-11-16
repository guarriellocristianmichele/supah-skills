# Interviews

Each buyer meets the offer once per round, as a stranger's product among real alternatives, and may walk away. Every rule here answers a measured failure (research note, sections "What LLM respondents get right and wrong" and "Sycophancy and what reduces it"):

| rule | failure it counters |
|---|---|
| the offer is a third party's product, and nobody says who asks | evaluations warm up when the asker owns or likes the work (Sharma et al.) |
| a fresh context per batch, never another buyer's answer | models conform to a visible majority (Weng et al.) |
| `nothing` is always an option, and the buyer is told leaving is normal | simulated customers rarely walk away unless told they may (Chen 2026) |
| options in the order `deal` recorded for that buyer | models favour the first option shown (Brand et al., Dominguez-Olmedo et al.) |
| prices stated as set by the seller, competitors at their real prices | a price change alone shifts unstated context (Gui and Toubia) |
| free reaction before the choice, intent judged later from it | asked for a 1 to 5 number, models answer 3 (Maier et al.) |
| a BUY names what it gives up | demand needs a trade-off to slope downwards (Brand et al.) |

## The cards

One card per option, the same shape for each, nothing styled to win:

```text
<Name> by <company>: <price> <currency> per <period>, set by the seller
<what it does, one sentence, plain words>
<how you get it: sign-up, download, sales call>
```

The offer's card uses the product's name and the words of `round.json`'s `offer`; its company is named as the seller, never as the person asking. Alternatives use the facts in `research.md`. The `nothing` card reads: `None of these: pay for no option above and carry on as now (<the buyer's current_solution>).` A buyer who already pays for an option on the cards and keeps it chooses that option, so a competitor's share counts the buyers who stay with it.

The choice is taken on the card's own terms: when the offer starts with a free trial, choosing it means starting the trial meaning to pay once it ends, and the give-up is what they stop paying for then. Asking only what they would pay for this month turns every trial into `nothing`.

## Worker brief

The unit brief for one batch; a worker gets this section, the cards, its batch's lines from `cards.jsonl` and those buyers' lines from `buyers.jsonl`, and nothing else (no brief, no research, no other batch, no hopes).

> You will answer as each of the buyers below, one at a time, in the order given. For each buyer: become that person, with their habits, current solution, budget, need and objection. You are shopping, not reviewing: nobody here made these products and nobody is waiting for a particular answer. Walking away is a normal answer, and so is taking an option that fits.
>
> Read the cards in the order listed for that buyer. Then write, as them, in their own voice:
>
> 1. **Reaction**: 40 to 80 words on what they think of the options, in plain speech, before deciding anything.
> 2. **Choice**: the one option they would actually take up this month on the terms its card states (paying, or starting a trial they mean to pay for when it ends), or `nothing`. An option they already pay for and would keep is a choice of that option.
> 3. **Give up**: when they chose the offer, what they stop paying for or doing to afford it once they pay (a named thing); otherwise leave it empty.
> 4. **Prices** for the offer, in the card's currency: at what price would it be so cheap they would doubt its quality (too cheap)? A bargain (cheap)? Getting expensive but still worth considering (expensive)? So expensive they would not consider it (too expensive)?
>
> Write one JSON line per buyer to your answers file, fields `buyer_id`, `round`, `options` (the ids in the order shown), `reaction`, `choice`, `give_up`, `price` with `too_cheap`, `cheap`, `expensive`, `too_expensive`. Finish one buyer's line before reading the next buyer.

Inline (no orchestrate): the same brief, one buyer at a time; write the line before reading the next buyer's record, and never reread earlier answers.
