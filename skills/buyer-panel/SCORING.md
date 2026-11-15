# Scoring

Intent is classified from the buyer's own words against fixed anchors, by a judge who never saw the buyer, the cards or the choice. Asked directly for a 1 to 5 rating, models answer mostly 3; a free reaction compared with anchor statements tracked human answers far better (Maier et al. 2025, research note). The skill uses a model judge instead of embeddings, since its scripts are standard library only; the anchors stay fixed so every round is measured alike.

## The five anchors

| intent | anchor statement |
|---|---|
| 5 | I would definitely buy this now; it is what I need at that price. |
| 4 | I would probably buy it; it fits what I need, with small doubts. |
| 3 | I might buy it, but I would need to know more or see it cheaper first. |
| 2 | I probably would not buy it; what I have now is good enough. |
| 1 | I would definitely not buy it; it is not for me. |

Changing an anchor changes every later number: it is a reviewed decision with a reason in the skill's ADR, never an edit for one round.

## Judge brief

The judge gets this section and `judge-input.jsonl` (buyer id and reaction, shuffled), nothing else.

> For each reaction below, pick the anchor statement whose meaning is closest to what the person says about buying: not the tone, not politeness, not how much they praise the product. A warm reaction that ends "but I'll stick with what I have" is a 2. Then name the main reason in a short tag of lowercase words joined by hyphens, reusing an earlier tag when the reason is the same (`already-paid`, `no-need`, `saves-time`, `too-expensive`, `trust`), and copy the few words of the reaction that carry the reason, exactly as written. Write one JSON line per reaction to `scores.jsonl`: `buyer_id`, `round`, `intent`, `reason`, `quote`.

Before scoring, read all reactions once and draft up to twelve tags, so the same reason gets the same tag across the round; add a tag later only for a reason none of them names.

## Intent weights

Stated intent overstates purchase: 15.3% of households said they would buy a computer within a year and 5.7% did (Sun and Morwitz 2010). The discounted BUY share counts each buyer who chose the offer at the weight of their intent, the top-box scheme Jamieson and Bass (1989) compared:

| intent | 5 | 4 | 3 | 2 | 1 |
|---|---|---|---|---|---|
| weight | 0.75 | 0.25 | 0.10 | 0.05 | 0.02 |

A buyer who chose an alternative or `nothing` counts 0 whatever their intent: the choice among real options is the stated purchase, the weight is how likely it converts. Raw share is always shown beside it, with the scheme's name; `aggregate --weights` takes another scheme, which the output then names as custom. A new product sits at the weak end of every finding on intent, so even the discounted share is a hypothesis.
