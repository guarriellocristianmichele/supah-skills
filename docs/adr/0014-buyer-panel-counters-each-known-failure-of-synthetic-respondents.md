# buyer-panel counters each known failure of synthetic respondents, keeps the same buyers across rounds, and reports every number as a hypothesis

A panel of model-written buyers is cheap and fast, and its errors are measured: agreement with whoever asks, too little spread, buyers who never leave, a pull to the first option, willingness to pay two to three times too high, and a 1 to 5 rating that collapses to 3 ([research note](../research/2026-11-synthetic-panels.md)). People overstate intent as well. The skill keeps the panel, because a hypothesis about which objection to test first is worth having, and gives each failure its own counter:

- Third-party framing: the idea reaches buyers as another company's product on a neutral card, and no brief says who asks or what they hope. Sharma et al. found feedback warms when the user says they wrote or like the work; SYCON Bench found answering as a third person resisted stance flips better than an instruction not to flatter.
- Fresh contexts: interviews run as an orchestrate job in small batches mixed across segments, each worker seeing only its batch. Every tested model conformed to a visible majority (BenchForm). Batches are the compromise between one context per buyer and cost; the round records the batch size and the report states it. Without orchestrate the skill goes one buyer at a time and says independence was partial.
- Walking away and order: real alternatives at real prices and "buy nothing" are always on the table, in an order the script shuffles per buyer and records. An explicit permission to disengage removed the push to purchase in Chen 2026; option position drove answers in Dominguez-Olmedo et al. and Brand et al.
- Free text, then anchors: buyers write a reaction before they choose; a judge who sees only the reaction places it on five fixed anchor statements. Semantic similarity rating against anchors matched human distributions where direct ratings did not (Maier et al.). The skill uses a model judge rather than embeddings, since its scripts are standard library only (ADR 0002), and keeps the anchors fixed so rounds compare.
- Discounted intent: the BUY share is shown raw and weighted by the top-box scheme Jamieson and Bass compared (75/25/10/5/2), the scheme always named, because stated intent over-predicts for people (Sun and Morwitz) and a new product sits at the weak end.
- Prices as an upper bound: the Van Westendorp range drops and counts out-of-order answers and is labelled an upper bound, after Brand et al. measured synthetic willingness to pay two to three times too high.
- Checks on every round: the script fails a round whose intent spread, share of buyers on one reason tag, reaction word overlap, praise density, raw BUY share or first-option choice rate crosses a threshold, and the verdict then says not to trust it. The research measured these failures but set no cutoffs, so each threshold is the skill's judgement, written down with its source and reason in the skill's reading reference.
- A separate critic: telling simulated respondents to play devil's advocate has no measured effect and would push every buyer one way, so one critic in its own context argues against the idea after the panel, as a report section of its own that never enters a buyer's answer.
- Segments as description: differences between buyer types name whom to talk to first and are never findings: Bisbee et al. saw a third of the differing coefficients flip sign.
- Grounding: only real results can say how wrong a panel is. Every report ends with a real test for the week, and a later mode stores the ratio between real and predicted results, so later panels in the project show a corrected figure next to the raw one.

The buyers are written once per panel and reused by every round, so a follow-up (a fix, a price, a pitch) is compared buyer by buyer instead of against a fresh, unrelated panel. A script computes every number from validated records; the model writes buyers, answers and the report's words, never a share or a price.

## Considered options

- One prompt that invents, pitches and counts in a single context: rejected; it carries every failure above, and the buyers read each other's answers.
- Asking intent as a 1 to 5 number: rejected; it collapses to the middle (Maier et al.).
- Embedding reactions against the anchors, as the published method does: rejected for now; it needs a model outside the standard library, and a judge applying the same fixed anchors keeps rounds comparable.
- A fresh panel for every question: rejected; nothing could be compared, and a change in the result could come from new buyers rather than from the change in the offer.
- Reporting a significance test between rounds: rejected; synthetic answers are not a sample of people, so the report shows noise and makes no significance claim.

## Consequences

- Every report opens with a line naming the model and saying the panel is simulated, and ends with a verdict and a real test.
- Changing an anchor statement, the default weights or a threshold is a reviewed change to this skill, with its source in the research note.
- The panel ledger lives in the project, and the user decides whether it is committed.
- buyer-panel adds edges to ADR 0012's call graph: orchestrate for interviews, ai-slop-prose for the report, ai-slop-design for the smoke-test page.
