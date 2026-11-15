# Craft

Build a page whose look comes from its subject. The first answer that arrives for a category is the reflex answer: write it down, treat it as spent, and choose past it on every axis.

Read `DIRECTION.md` and `REFLEXES.md` (in this folder) in full before step 2.

1. **Subject**: from the brief, name the subject, the audience, the page's primary job (what a visitor should do or understand) and its category in `CATEGORIES.md`; read that category's section (two sections when the work spans two surfaces). Its frame and floor bind every later step; its room and accessory budget set how far the direction goes. When the brief leaves one open, ask with options built from the brief (likely audiences, likely jobs) before going on. Read `PRODUCT.md` / `DESIGN.md` and the project's tokens when present: an identity the brand already committed to is followed, and the steps below choose only what it leaves open.
2. **Scene and voice**: one sentence of who uses the page, where, under what light and in what mood, specific enough to settle light versus dark. Three voice words that name physical objects, not adjectives of quality.
3. **Reflex answer**: write the page you would build for this category without thinking: palette, fonts, hero, section order, motion, imagery. Then read `.slop-design/history.md` when it exists and add every direction already used in this project. Everything on this list is spent.
4. **Direction**, each axis with the reason it fits this subject:
   - palette: 4 to 6 named colours in OKLCH, and the strategy that sets their proportions;
   - type: faces and roles, chosen with DIRECTION.md's font procedure;
   - layout: the concept in one sentence and an ASCII wireframe of the first two screens, at 390 pixels and at desktop width;
   - one memorable element, the single place boldness is spent;
   - one motion moment, or none, with the reason;
   - imagery: what is shown, and where it comes from.

   Done when all six axes are written with their reasons.
5. **Check the direction** against the reflex answer, the lanes in REFLEXES.md and the category's reflexes, axis by axis, then as a whole against the category's frame and accessory budget. An axis that matches is revised, and you say what changed and why. In an interactive session, show the direction and ask with options: build it, change one named axis, or see a second direction. Done when no axis matches and the direction is approved, or the session is not interactive.

   Variants (`craft <brief> variants 3`): write that many directions that differ from the reflex answer and from each other on palette, type and layout concept, each checked as above. Build them with the `orchestrate` skill when installed: job `design-variants`, profile `build`, units = directions, unit brief = steps 6 to 8 for one direction, each worker writing only inside its own folder (`<target>/variant-<n>/`). Without orchestrate, build them in sequence. Ask with options which one to keep; step 9 records the pick.
6. **Build** to the direction and DIRECTION.md's quality floor, with the brief's real content.
7. **Sweep** the files you built: SWEEP.md steps 3 to 9. A hit on a choice the direction made on purpose is `chosen: brief`.
8. **Look**: with a browser tool, screenshots at 390, 768 and 1440 pixels wide, each checked against DIRECTION.md's responsive checks and for horizontal scroll. Compare them with the direction, then remove one accessory: the decoration that serves the brief least.
9. **Record**: append the direction to `.slop-design/history.md` (date, subject, palette, fonts, layout concept, memorable element).

**Completion.** Every axis of the direction differs from the reflex answer, each with its reason; the sweep's rescan exits 0 with verdicts recorded; the screenshots were judged or reported unavailable; and the history has the new block.
