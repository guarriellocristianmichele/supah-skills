# Price

Run the same buyers at three prices and name the one that earns most. `P` below is the panel folder, `.buyer-panel/<slug>/`; `panel.py` is `python "${CLAUDE_SKILL_DIR}/scripts/panel.py"`.

Read `INTERVIEW.md` before step 3 and `READING.md` before step 5 (both in this folder). A price round is a round like any other: only the price on the offer's card changes.

1. **Panel.** Pick the panel as SKILL.md says (no arguments: ask which panel). It needs a round that `aggregate` accepts, `r1` unless the user names another: the **base round**. No panel yet: say so and offer `run`. Done when `P` and the base round are known.
2. **Prices.** With three prices after `price` in `$ARGUMENTS` (numbers, distinct, in the base round's currency), use them. Otherwise run `panel.py prices P/rounds/<base>` and ask with options: **use these three** (recommended: the low end, the indifference point and the high end of the base round's price range), **rounded**, the same three moved to prices a seller would print (show them), or **my own three**. When `prices` returns none (no range: every price answer was out of order), ask for three prices, offering the brief's price with the alternatives' prices as one ready answer. Say in the question that the range is an upper bound, so the high price is likely too high. Done when three distinct prices are settled.
3. **Rounds.** Take the next free price run `n` (`p1` when no `p1-*` round exists) and label each round `p<n>-<price>`. For each price, follow RUN.md steps 8 to 11 with a copy of the base round's `round.json` where only `label`, `price` and `seed` change: same offer, options, currency and model, a fresh `deal`, its own orchestrate job `buyer-panel-<slug>-<label>` (or inline, one buyer at a time), its own judge. Run the rounds one after another, never in one job, so no context sees a buyer at two prices; the base round is never reused, even at the same price, so the three rounds run under the same conditions. Done when `aggregate` exits 0 on all three.
4. **Revenue.** `panel.py --json revenue P/rounds/p<n>-<low> P/rounds/p<n>-<mid> P/rounds/p<n>-<high>`. Exit 2 means the rounds differ in more than the price: fix the `round.json` it names. Exit 3 names records at fault: re-interview or re-judge those buyers. Never edit an answer or a score to make it pass. Then run it once more without `--json` for the Markdown summary and table. Buyers it lists as left out lack an answer or a score in some round; re-run them or name how many in the verdict.
5. **Report.** Write `P/price-p<n>.md`:

   ```text
   Simulated panel: <N> synthetic buyers written by <model>, not real people. Every number below is a hypothesis to test on people.

   # <idea in one line>, price run p<n>: <low> / <mid> / <high> <currency>

   ## Revenue by price
   <revenue's summary lines and table, unchanged>

   ## Each price
   <for each round, aggregate's summary lines (BUY share, top reasons, price range), unchanged>

   ## How these rounds were run
   <as READING.md's report, once for all three rounds: the base round, where the prices came from, batch size or partial independence, one judge per round, the weights, whether ai-slop-prose swept this report>

   ## Verdict on price
   <the price that earns most and its revenue next to the other two; when the raw buyers would pick another price, say so and why the pick rests on discounted buyers; when the pick is the lowest or highest price tested, say the peak may lie beyond the prices tried and offer another price run around it>

   ## First real test this week
   <the test that would confirm the pick, its cost, and the result that would change it>
   ```

   Synthetic buyers state willingness to pay two to three times too high (research note, "Pricing questions that work in a survey"): write that every price here is an upper bound and that revenue is relative, a way to rank the three prices, never a forecast. The real test, from READING.md's list, at the picked price: **a pre-sale** to three people of the most likely buyer type at that price, or **a smoke test** that shows the picked price to half the visitors and the next lower one to the other half and counts sign-ups or deposits at each. State the threshold before the test runs.
6. **Sweep.** With ai-slop-prose installed, run its sweep on the report with purpose `panel report`; it may rewrite the prose, never a number, quote or table row. Without it, the method section says the report was not swept.
7. **History.** Append one line per round to `P/history.md` as RUN.md step 14 does, then one line for the run: date, `p<n>`, the three prices, the price that earns most and its revenue, the verdict.

**Completion.** Three rounds `p<n>-<price>` exist, differing from the base round only in label, price and seed; `aggregate` exits 0 on each and `revenue` exits 0 on the three; `P/price-p<n>.md` opens with the simulated-panel line naming the model, holds `revenue`'s output unchanged, names the price that earns most, says the prices are an upper bound, and ends with the real test that would confirm the pick and its threshold; the history has the four lines.
