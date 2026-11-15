# Test

Turn a panel round into the first test on real people: an interview script, a smoke-test landing brief, and the thresholds that decide go or stop, written before anything goes live. `P` is the panel folder, `K` is `P/test/`, `panel.py` is `python "${CLAUDE_SKILL_DIR}/scripts/panel.py"`. This mode writes the kit; the user runs the test.

Read `RECORDS.md` (the `test.json` section) before step 6 and `READING.md` ("The first real test") before step 3 (both in this folder).

1. **Panel and round.** With one panel in the ledger, take it; with several, ask with options which one. Take the round the user names, or the last one in `P/history.md`. When `K/test.json` already exists, ask with options: **keep it** (a test is running or done; show its thresholds and stop), **write a new kit** (move `K` to `P/test-<written date>/`, so the old thresholds stay as they were), or **stop**. Never edit the thresholds of a test that has gone live. Done when the round is chosen and `K` is free.
2. **Objections.** `panel.py --json objections P/rounds/<label>` gives the round's top three pass reasons, each with the buyers who gave it, their words, what they use now and what they last spent, the buyer type most likely to buy, and the panel's raw and discounted BUY share. Exit 3 means the round's records are not valid: fix them as in RUN.md step 11 and run it again. Done when it exits 0.
3. **Which test.** Ask with options:
   - **interviews and a smoke test** (recommended): five interviews find out whether the top objection holds; the landing page shows whether anyone acts;
   - **interviews only**: when the top reason is no need at all, or unclear;
   - **smoke test only**: when the reasons are clear and the doubt is whether anyone acts.

   Then, for the smoke test, ask the one action it measures: **a sign-up** (recommended for a first test: cheap to ask, cheap to give) or **a pre-order** (a deposit or a card held at the round's price: fewer people, a stronger signal). Done when the parts and the action are chosen.
4. **Interview script.** Write `K/interview.md`, the Mom Test (research note, "Cheap real-world validation to end with"): talk about their life, not the idea; ask about specifics in the past; count only commitments.
   - who: five people of the likely buyer type, and where to find them (from `research.md`: the communities, tools and places that type already uses). Never people who already know the idea.
   - opening: one line asking for 20 minutes about how they handle the job the offer does, with no mention of the offer.
   - questions: for each top objection, two or three questions about the last time it happened and what it cost: "When did you last ...?", "What did you use?", "What did you pay for it, and who paid?", "What did you try before that, and why did you stop?". Build them from the buyers' current solutions and last spend; under each, name the objection it probes and the buyer ids whose words prompted it. Add one question about the most recent purchase in the category.
   - never asked: anything about the offer, its name or its price; "would you", "will you", "do you think", "imagine", "how much would you pay"; any question whose answer is a compliment or a promise about the future.
   - closing: only after the questions, describe the offer in one sentence and ask for one commitment that costs something: time (a follow-up session with their own material), reputation (an introduction to the person who decides) or money (a pre-order at the round's price). A compliment, "sounds great" or "let me know when it's out" is no commitment.
   - notes: a block to copy per interview: date, who (type, no name in a shared file), the facts (last time, what they used, what they paid), the commitment (`none`, `time`, `reputation`, `money`).

   Done when every question asks about a past event or a real amount, none names the offer or its price, and the script ends with the commitment request.
5. **Landing brief.** For a smoke test, write `K/landing.md`:
   - offer: what it does, in the round's offer text; the price as the seller sets it (the round's price and currency); for whom (the likely buyer type).
   - the one action: the button and what it does (a sign-up form, or a pre-order). Nothing else on the page asks for an action.
   - objections the page answers: the top objections with the buyers' own words, and what the page says to each; only claims the offer can keep.
   - traffic: where visitors come from (the same places as step 4), and how many visits the sample needs (step 6).
   - measure: visits and actions counted by one tool, and the date the test ends.
   - honesty: it is a fake door: after the action, say plainly that the product is not built yet and when the visitor will hear more; a pre-order takes no money until the product exists, or is refunded on request. No made-up testimonials, logos, user counts or scarcity.

   Then build the page: with ai-slop-design installed, read its `SKILL.md` and `CRAFT.md` from `${CLAUDE_SKILL_DIR}/../ai-slop-design/` (or wherever the agent finds that skill) and follow `craft` with `K/landing.md` as the brief, building into the folder the user picks (ask with options: `K/landing/`, recommended, or a path in their project). Without it, keep the brief and tell the user to run `/ai-slop-design craft` with it once installed, or to hand it to whoever builds the page. Done when the brief exists and the page is built or handed over.
6. **Thresholds.** Before the test runs, set go and stop for each metric the kit uses: `commitments` (interviews that end in a commitment), and the smoke test's action, `signups` or `preorders`, both taken of visits. Propose these starting points and ask with options: **use them**, **set them from your numbers** (the share of visits at which the price pays for the traffic, or the pre-orders that cover a first batch), **set your own**:

   | metric | go at or above | stop at or below | sample |
   |---|---|---|---|
   | commitments | 2 of 5 interviews (0.4) | 0 of 5 (0) | 5 interviews |
   | signups | 0.05 of visits | 0.01 of visits | 300 visits |
   | preorders | 0.01 of visits | 0.002 of visits | 300 visits |

   They are starting points, not benchmarks from research. The panel's discounted share is an upper bound (READING.md): never set a go threshold from it. Set `ends` within two weeks of today. Write `K/test.json` with `written` set to today; done when `panel.py validate K/test.json` exits 0. Then show the thresholds as "go at N of M, stop at N of M" and say that they are fixed: changing one after the test goes live means a new kit.
7. **Sweep.** With ai-slop-prose installed, run its sweep on `K/interview.md` with purpose `interview script` and on `K/landing.md` with purpose `landing page brief`; it may rewrite the prose, never a question's subject, a quote, a price or a threshold. Without it, add a line to each file saying it was not swept.
8. **History.** Append one line to `P/history.md`: date, `test` from round `<label>`, the parts, each metric's go and stop, the sample, the end date.

**Completion.** `K/test.json` validates and was written before the test went live; `K/interview.md` asks only about past behaviour and real spend, names no offer or price before the closing, and ends with a commitment request; for a smoke test, `K/landing.md` names the offer, the price and the one action, and the page was built through ai-slop-design or handed over; the kit was swept or says it was not; the history has the line.
