# Craft

Build a page whose look comes from its subject. The first answer that arrives for a category is the reflex answer: write it down, treat it as spent, and choose past it on every axis.

Read `DIRECTION.md` and `REFLEXES.md` (in this folder) in full before step 3.

## Restyle

`craft <surface>` gives an existing surface a new direction: a page or route named by its path or its files, usually one a sweep or a plan marked `handoff`. An argument that names a file, folder or route in the repo is a surface; anything else is a brief; when it could be either, ask with options. The steps below run as for a brief, with these changes:

- **Brief**: the brief is read from the surface, never asked for. Read its files and, with the browser the user allowed, the running page: subject, audience, primary job and category come from what the page says and does (step 1). Ask with options only what the page leaves open.
- **Inventory**, before any edit: snapshot each file to the scratchpad as `<name>.orig` and list what must survive: every visible string in order, every link and its target, every form with its fields, names and actions, every event handler, prop, route and data call, and every accessible name, role and alt text.
- **Lane**: the lane the handoff named, from the sweep report, the handoff batch in `.slop-design/plan.md` or the reason of the keep file's `handoff` lines. When none was named, judge which REFLEXES.md lane the page sits in now and write it down. The surface's current look, its lane included, goes into step 4's reflex answer.
- **Several surfaces in one handoff**: restyle the first, then each next one with the same direction, so they stay one site; the history block of an earlier surface in the same handoff is the direction to follow, not a spent one.
- **Build** (step 7) edits the surface's files in place: markup structure, classes, styles, tokens and assets may change; strings, handlers, props, data calls and routes may not. A direction that needs other copy or a new section is out of scope: list it in the report for the user.
- **Content check**, before step 8: compare the inventory with the restyled files: the same strings in the same order, the same links, fields, handlers and accessible names. A difference is reverted, not kept.
- **Look** (step 9): screenshot the surface before the build too, at the same widths, so the report shows both.
- **Record** (step 10): the block also names the surface and the lane it left.

Variants apply to `craft <brief>` only.

## Steps

1. **Subject**: from the brief (restyle: from the surface), name the subject, the audience, the page's primary job (what a visitor should do or understand) and its category in `CATEGORIES.md`; read that category's section (two sections when the work spans two surfaces). Its frame and floor bind every later step; its room and accessory budget set how far the direction goes. When the brief leaves one open, ask with options built from the brief (likely audiences, likely jobs) before going on. Read `PRODUCT.md` / `DESIGN.md` and the project's tokens when present: an identity the brand already committed to is followed, and the steps below choose only what it leaves open.
2. **Research**: ask with options whether to browse (SKILL.md, browser tool), and what: current work in the category, the competitors the brief names, both, or nothing. With the user's yes, look at 4 to 6 sites: recent picks in the category from galleries such as Awwwards, Siteinspire, Godly or Mobbin, and each named competitor. Note per site, in one line each, what it does for its subject and what it shares with the others. What most of them share goes into step 4's reflex answer; what only one does well is a reference, never a template. Done when the notes exist, or the user said no.
3. **Scene and voice**: one sentence of who uses the page, where, under what light and in what mood, specific enough to settle light versus dark. Three voice words that name physical objects, not adjectives of quality.
4. **Reflex answer**: write the page you would build for this category without thinking, plus what step 2 found most sites share: palette, fonts, hero, section order, motion, imagery. Then read `.slop-design/history.md` when it exists and add every direction already used in this project. A restyle adds the surface's current look and its lane. Everything on this list is spent.
5. **Direction**, each axis with the reason it fits this subject:
   - palette: 4 to 6 named colours in OKLCH, and the strategy that sets their proportions;
   - type: faces and roles, chosen with DIRECTION.md's font procedure (with a browser, open the catalogue and the specimen of the pick);
   - layout: the concept in one sentence and an ASCII wireframe of the first two screens, at 390 pixels and at desktop width;
   - one memorable element, the single place boldness is spent;
   - one motion moment, or none, with the reason;
   - imagery: what is shown, and where it comes from (with a browser, open every stock URL to confirm it resolves).

   Done when all six axes are written with their reasons.
6. **Check the direction** against the reflex answer, the lanes in REFLEXES.md and the category's reflexes, axis by axis, then as a whole against the category's frame and accessory budget. An axis that matches is revised, and you say what changed and why. A restyle also names the handoff's lane and checks every axis against it: an axis that matches the lane is revised even when it differs from the reflex answer. In an interactive session, show the direction and ask with options: build it, change one named axis, or see a second direction. Done when no axis matches and the direction is approved, or the session is not interactive.

   Variants (`craft <brief> variants 3`): write that many directions that differ from the reflex answer and from each other on palette, type and layout concept, each checked as above. Build them with the `orchestrate` skill when installed: job `design-variants`, profile `build`, units = directions, unit brief = steps 7 to 9 for one direction, each worker writing only inside its own folder (`<target>/variant-<n>/`). Without orchestrate, build them in sequence. Ask with options which one to keep; step 10 records the pick.
7. **Build** to the direction and DIRECTION.md's quality floor, with the brief's real content.
8. **Sweep** the files you built: SWEEP.md steps 3 to 9. A hit on a choice the direction made on purpose is `chosen: brief`.
9. **Look**: with the browser the user allowed, screenshots at 390, 768 and 1440 pixels wide, each checked against DIRECTION.md's responsive checks and for horizontal scroll. Compare them with the direction, then remove one accessory: the decoration that serves the brief least.
10. **Record**: append the direction to `.slop-design/history.md` (date, subject, palette, fonts, layout concept, memorable element).

**Completion.** Every axis of the direction differs from the reflex answer, each with its reason; the sweep's rescan exits 0 with verdicts recorded; the research notes exist or the user declined them; the screenshots were judged or reported unavailable; and the history has the new block. A restyle also leaves the surface's content and behaviour unchanged against the inventory, with no axis in the handoff's lane.
