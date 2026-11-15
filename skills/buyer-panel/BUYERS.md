# Building buyers

Buyers are written once per panel and never edited after the first round, so rounds compare buyer by buyer. Two failures shape this file: synthetic samples are too alike (a spread about half a human sample's, groups flattened; research note, "What LLM respondents get right and wrong"), and buyers invented without a market get budgets and alternatives from the model's guess.

## The segment plan

- Segments are groups that differ in how they buy, not in demographics alone: a solo freelancer and a four-person studio spend differently even at the same age. Three to six segments; one segment of the audience the brief may have missed (people who buy nothing in the category today) when the research shows they exist.
- Each segment's share is the part of the audience it makes up, from the research when it says so; otherwise an even split, said in `research.md` as an assumption.
- Each budget range is what that segment spends in the category per period (month or year, stated once in `research.md`), from prices of what they already pay for, category surveys and the alternatives' plans. A range nobody could source is marked an assumption, and the report says so.

## Each buyer

- `segment` per the plan, in proportion to the shares (round to whole buyers; the largest segments absorb the remainder).
- `budget` spread across the segment's range, not bunched in the middle: place the first buyer of a segment near the low end, the next near the high end, and fill between.
- `name`: a plausible name for the segment and the countries the brief targets, never a famous name; no two alike.
- `habits`: one or two sentences of concrete behaviour where the product would fit (how often, with what, for whom), no adjectives about personality.
- `current_solution`: what they use now, drawn from the research's alternatives in the proportions it suggests, plus `nothing`, a spreadsheet, paper or a person doing it by hand where that is real.
- `last_spend`: what they last paid in the category, consistent with the budget and the current solution (0 is common and honest).
- `objection`: one honest reason this buyer might not buy anything new, specific to their situation ("IT will not approve a new vendor"), never a generic "too expensive". No two buyers share an objection word for word.

## What not to write

- Any hint of who is asking, that the idea is the user's, or that the panel is about this idea: buyers describe a market, not an audience for one product.
- An opinion of the idea: buyers have not seen it yet.
- Buyers built to like or reject it: if a segment would obviously pass, it stays in the plan at its share.
