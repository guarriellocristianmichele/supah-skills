# Design reflexes: sources, licences and prevalence

Research behind `skills/ai-slop-design/REFLEXES.md` and `designscan.py`, gathered on 2026-11-14 from the repositories below (read through the GitHub API) and the one quantified study found. Rule ideas were ported and the text written fresh; no source text is copied.

## Sources

- **impeccable** ([pbakaus/impeccable](https://github.com/pbakaus/impeccable), Apache-2.0, started from Anthropic's frontend-design). Its detector is a Rust workspace run as `npx impeccable detect`: source files get regex rules only, URLs get the full set through Chrome's DevTools protocol and computed styles. 62 rules in `antipatterns.json`, split into slop (side tab, gradient text, overused font, AI colour palette, cream palette, nested cards, dark glow, hero eyebrow chip, numbered section labels, bounce easing, marquee…) and quality (contrast, line length, tiny text, skipped headings, DESIGN.md drift). Its unit tests carry negative cases (a 2×2 rounded dot is not a side stripe; a spinner's `border-b-2` is not flagged), which became fixtures here. The idea of category reflexes at two altitudes (guessable from the category, then from the category plus what it avoids) comes from its reference files.
- **frontend-design** ([anthropics/skills](https://github.com/anthropics/skills), Apache-2.0). Five calibration clusters: cream `#F4F1EA` with a serif and terracotta `#D97757`; near-black with one acid accent; broadsheet hairlines; the SaaS card kit; template chrome (tracked caps eyebrows, `A · B · C`, `WORD — fragment`, `#0B0B0B`, mono labels, `→` on links). Also: work in two passes, plan then review against the generic default, and spend boldness in one place.
- **taste-skill** ([Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill), MIT). The 2026-02 version listed about a hundred tells (`#667eea → #764ba2`, `from-indigo-500 to-purple-600`, a white card with `#E5E7EB` border and shadow, three equal columns, Acme, Jane Doe, `555-` numbers, `href="#"`). The current version deals palettes and layouts at random with a history file so pages differ; the history idea became `.slop-design/history.md`.
- **hallmark** ([Nutlope/hallmark](https://github.com/Nutlope/hallmark), MIT). About 75 gates with a tier (never waived, waivable with a recorded reason) and a class saying who checks it (static, render, judged). Floor bans include purple-to-blue gradients, emoji as icons, drawn browser windows (`traffic-light`, `url-pill`, `title-bar`), `transition: all`, one italic word in a roman heading, middle-dot meta and glued arrows.
- **design-slop-cop** ([AdrianKrebs/design-slop-cop](https://github.com/AdrianKrebs/design-slop-cop), MIT) and its study ([adriankrebs.ch/blog/design-slop](https://www.adriankrebs.ch/blog/design-slop/), April 2026). Playwright loads each page and one script per pattern checks the DOM and computed styles with numeric thresholds. Its `dataset/labels.jsonl` holds per-pattern labels for about 190 sites; `calibrate_design.py` uses it as the AI-era corpus.
- **unslop-ui / vibecoded-design-tells** ([JCarterJohnson/vibecoded-design-tells](https://github.com/JCarterJohnson/vibecoded-design-tells), MIT for code only; its harvested Reddit text is excluded from the licence and is not used here). Its main warning shaped the scanner's tiers: over-flagging (dark mode, bento grids, mesh backgrounds, themed shadcn) makes an audit noise.
- **ui-ux-pro-max** ([nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill), MIT). Useful for UX rules, but its reasoning table recommends the hero, features and CTA template with glass for SaaS: the pattern the other sources flag.
- **awesome-design-md** ([VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md), MIT). DESIGN.md files describing real brands. The format is a useful input; the files themselves describe other companies' trade dress, so none is shipped or used as a template.

## Prevalence

From the design-slop-cop study of 500 Show HN sites (share of sites with the pattern): gradients 28%, default shadcn 23.5%, centred hero 23.5%, permanent dark mode with grey text and caps labels 20.3%, three or six identical icon cards 20.1%, glass panels 17.1%, reflex fonts 15.8%, top or left accent stripe 13%, stat banner 12.2%, purple or indigo CTA 10.7%, all-caps labels 10.5%, numbered steps 9.4%, pill badge above the headline 4.7%, vivid coloured shadows 4.3%, emoji in nav 3.8%. The author reports 5 to 10% false positives.

## Where the sources disagree

- Glass panels: banned by taste-skill's 2026-02 list and by impeccable as a default, recommended by ui-ux-pro-max, cleared by unslop-ui's data. Here: W, and never on a sticky or fixed bar.
- Dark mode, bento grids, mesh backgrounds: flagged by some, cleared by unslop-ui. Here: not rules.
- Em dashes: hallmark bans them in copy; copy belongs to ai-slop-prose, which has its own calibrated rule.

## Additions beyond the sources

- `low-contrast` computes the WCAG 2 ratio from Tailwind's default palette (v3.4.17, MIT, bundled as `tailwind-colors.json`) or from literal CSS colours, only where text and background are declared on the same element.
- The responsive rules (`missing-viewport`, `fixed-width`, `unprefixed-grid`, `hover-only`, `tiny-text`, `viewport-width`) find source that cannot adapt to a phone; WCAG 2.2's reflow criterion (1.4.10) and target size minimum (2.5.8) are the basis, and the screenshot checks at 390, 768 and 1440 pixels cover what source cannot show.
- `repeated-class-string`, `duplicate-css-block` and `untokened-colour` count styles copied across the files of one scan, where a component, class or token would hold them once.
