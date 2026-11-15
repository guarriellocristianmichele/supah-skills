# Reflexes

Nine categories, swept in this order, then the judgment-only list. `rule` names are scanner rule ids; `designscan.py rules` prints the tier each one ships with. Tiers: **S** fix on one sighting; **M** fix unless a keep reason applies; **W** read each hit and fix the ones nothing chose.

Each rule says what it matches, why it reads as a reflex, the keep reasons that usually apply, and the fix direction. A fix moves the page toward its subject: swapping one reflex for the next one on the list (purple gradient to teal gradient, Inter to Geist) is not a fix.

## 1. colour

- `purple-gradient`: Tailwind `from-purple/violet/indigo/fuchsia-*` paired with a blue, pink, cyan or purple stop, or a CSS gradient with the stock hexes (`#667eea`, `#764ba2`, `#6366f1`, `#8b5cf6`…). The most cited tell in every source, and the most frequent on 2026 launch pages. Keep: `brand`. Fix: one solid colour from the subject's palette; a gradient only when it depicts something (light, depth, a material).
- `stock-swatch`: `bg-indigo-500/600/700`, `bg-violet-*`, `bg-purple-*`, `bg-blue-600` as a fill. Untouched Tailwind defaults read as "no one chose this". Keep: `brand`. Fix: a named token from the direction, tuned off the default swatch.
- `cream-clay`: a cream ground (`#f4f1ea` family) with a terracotta or clay accent (`#d97757` family) in the same file. The 2026 "tasteful default", and the accent of Claude's own interface. Keep: `brand`. Fix: derive ground and accent from the subject's materials.
- `pure-black-white`: literal `#000`/`#fff` outside a custom property. Untinted extremes look harsh and unchosen. Keep: `content` (a logo spec, a print colour). Fix: tinted neutrals toward the palette's hue; define the extremes once as tokens.
- `near-black`: `#0b0b0b`, `#111`, `#121212`… The stand-in black of generated dark themes. Fix: a dark tinted toward the palette's hue, or real black when the subject is literally black.
- `low-contrast`: a text and background colour declared on the same element (Tailwind classes or one CSS block) below WCAG AA: 4.5:1, or 3:1 for large text. Grey text on near-black is the usual case. Keep: `a11y` only for disabled or decorative text that carries no information. Fix: raise the text's lightness until it passes; the ratio is in the match.

## 2. type

- `reflex-font`: the primary face of a `font-family`, a Google Fonts link, a `next/font/google` import or an `@fontsource` package is on the dated reflex list (Inter, Geist, Roboto, Poppins, Space Grotesk, Fraunces, Instrument Serif, Playfair Display, DM Sans…). Training-data defaults; they make every page sound alike. Keep: `brand`. Fix: DIRECTION.md's font procedure. Moving to the next name on the list is not a fix.
- `accent-word-heading`: a heading with one word in italic, a colour or a gradient. Keep: `brief` when the brief asks for it. Fix: let size, weight and space carry the heading; emphasis comes from the sentence.
- `eyebrow`: small tracked caps right before a heading. Repeated above every section, it is template grammar. Keep: `brand` when it is a named system used once or twice. Fix: delete it, or fold its information into the heading.
- `tracked-caps`: small uppercase text with wide tracking elsewhere (labels, badges, nav). Keep: `content` for real short labels. Fix: sentence case at a readable size.
- `mono-label`: monospace for small labels on a page that is not about code. Mono as costume for "technical". Keep: `content` for code, data, version strings. Fix: the body face, or a figure style (tabular numbers) when alignment matters.

## 3. surface

- `gradient-text`: `bg-clip-text text-transparent`, `background-clip: text`. Decorative, and fragile for contrast. Keep: `brand`. Fix: a solid colour; emphasis through weight or size.
- `glass-card`: backdrop blur on a translucent panel that is not a sticky or fixed bar. Keep: `content` when something real sits behind it (a map, a video). Fix: an opaque surface with a tinted background, or no container.
- `coloured-glow`: a zero-offset coloured shadow (`shadow-[0_0_30px_rgba(…)]`, `box-shadow: 0 0 20px <hue>`), coloured Tailwind shadows. Neon on dark, the second-most common tell. Fix: no glow; depth from a real light direction, or flat.
- `accent-stripe`: a thick left or top border in colour on a rounded box (`border-l-4 border-indigo-500 rounded-lg`, `border-left: 4px solid`). Keep: `content` for a diff, a quote convention the site already uses. Fix: a full border, a background tint, a leading mark, or nothing.
- `shadcn-card`: the default shadcn card string untouched. Keep: `brand` when the design system themed it on purpose. Fix: theme the component (radius, border, surface) to the direction.
- `uniform-radius`: one radius on at least 80% of rounded elements (6 or more). Hierarchy flattened into one shape. Fix: radius by role (controls, cards, media differ), or none.
- `soft-shadow`: the same soft grey shadow on most surfaces. Fix: elevation only where something floats; separate the rest with space or rules.

## 4. layout

- `icon-card-grid`: a three-column grid of cards, each with an icon tile, a heading and a line of text. The hero-features-CTA skeleton in one element. Keep: `content` when there really are three parallel things a visitor compares. Fix: the content's real shape: a list, a table, a sequence, one feature shown large, a demo.
- `numbered-markers`: `01`, `02`, `03` as labels. Keep: `sequence` when the content is steps or a timeline. Fix: drop the numbers.
- `stat-banner`: three or more big numbers with suffixes (`10,000+`, `99.9%`, `5x`) close together. Keep: `content` when the figures are real and sourced. Fix: one real figure in a sentence, or proof that shows instead of counting (a screenshot, a quote with a name).
- `vh-hero`: a hero section sized to the viewport (`h-screen`, `min-height: 100vh`). Pushes content below the fold and breaks on mobile browsers. Fix: height from content; when full-bleed matters, `svh` with a cap.
- `faux-chrome`: a drawn browser or window (traffic-light dots, URL bar, title bar). Keep: `content` for a real screenshot's frame. Fix: show the real product screenshot, cropped to what matters.

## 5. glyph

- `emoji-icon`: an emoji as an icon in a heading, nav item, list or `icon:` field. Fix: an icon from one consistent set, or no icon; words carry meaning.
- `middot-meta`: `A · B · C` strings. Fix: the one fact that matters, or a list.
- `glued-arrow`: `→` appended to link or button text. Fix: a verb that says where the link goes; an icon, if any, from the icon set and outside the label.
- `word-dash-label`: `WORD — fragment` labels. Fix: a sentence-case label.
- `pulsing-dot`: a small `animate-ping`/`animate-pulse` dot. Keep: `content` when it reports a live status. Fix: remove it.

## 6. motion

- `transition-all`: `transition: all`, `transition-all`. Animates layout and colour by accident and costs performance. Fix: name the properties (`transition-colors`, `transform`, `opacity`).
- `reveal-every-section`: four or more scroll reveals in a file (`whileInView`, `data-aos`, `fade-up`). Fix: one orchestrated moment, or none; content visible without JavaScript.
- `bounce-easing`: overshooting `cubic-bezier`, back, elastic or bounce easings. Fix: exponential ease-out (quart, quint, expo).
- `hover-scale`: three or more `hover:scale-*` or lift effects. Fix: hover feedback that fits the element (colour, underline, cursor), and motion only where it answers an action.
- `no-reduced-motion`: animation in a file with no `prefers-reduced-motion` path. Keep: `a11y` when the project handles it globally (check the global stylesheet). Fix: wrap the motion in `prefers-reduced-motion: no-preference` or `motion-safe:`.

## 7. placeholder

- `placeholder-name`: Acme, Jane Doe, John Doe, Lorem ipsum. Fix: the brief's real content, or a question to the user.
- `placeholder-phone`: `555` numbers. Fix: the real number, or remove it.
- `dead-link`: `href="#"`. Fix: the real destination, or a `<button>` when it triggers an action.

## 8. responsive

Most visitors arrive on a phone. These rules find source that cannot adapt; the screenshots in step 6 find the rest.

- `missing-viewport`: an HTML document with no `<meta name="viewport">`. Phones render it as a shrunken desktop page. Fix: `<meta name="viewport" content="width=device-width, initial-scale=1">`.
- `fixed-width`: a container fixed at 400 pixels or more (`w-[1200px]`, `width: 1140px`) with no `max-width`. It forces horizontal scrolling on small screens. Fix: `max-width` plus fluid width (`w-full max-w-6xl`, `width: min(100%, 70rem)`).
- `unprefixed-grid`: three or more grid columns at every width (`grid-cols-3` with no `md:` variant, `repeat(3, 1fr)` in a stylesheet with no media or container query). Fix: one column by default and more at a breakpoint the content needs, or `repeat(auto-fit, minmax(16rem, 1fr))`.
- `hover-only`: content revealed only on hover (`opacity-0 group-hover:opacity-100` with no focus variant). Touch screens and keyboards never reach it. Fix: visible by default on touch, or the same reveal on `focus-within`.
- `tiny-text`: text set below 12 pixels. Fix: 12 pixels at the very least for labels, 16 for body text on phones; use `clamp()` for type that scales.
- `viewport-width`: `w-screen` or `100vw`, which includes the scrollbar and overflows on desktop. Fix: `w-full` or `100%`.

## 9. duplication

Counted across every file of one scan, so pass all the files of a feature together.

- `repeated-class-string`: the same class string of six or more tokens three or more times. The copy-paste a generated codebase grows instead of a component. Fix: one component, a `cva` variant or a shared class, used everywhere.
- `duplicate-css-block`: the same three or more declarations under two or more selectors. Fix: one class, or a shared selector list.
- `untokened-colour`: one literal hex colour used five or more times outside a custom property. Fix: a named token (custom property or Tailwind theme colour), referenced everywhere.

## Judgment-only

Read the page as a whole for these; no pattern finds them.

- The category test: could someone guess the palette and theme from the category alone ("fintech, so navy and gold")? Then the page took the first reflex.
- The second-order test: could someone guess the aesthetic from the category plus what it avoids ("AI tool that is not SaaS-cream, so editorial serif")? Then it took the reflex one level down.
- The template skeleton: hero, three features, social proof, pricing, CTA, footer, in that order, whatever the subject.
- Motion sprinkled on every section instead of one moment that answers the content.
- No single memorable element, or boldness spent everywhere at once.
- Copy that sells instead of saying what the product does (hand it to ai-slop-prose).
- Fake product UI built from styled boxes where a real screenshot exists.
- Imagery missing on a subject that is visual (food, places, objects), or stock imagery that could belong to any brand.

### Lanes

A **lane** is a saturated aesthetic family. A page can avoid every rule above and still sit in one. Name the lane in a handoff; in craft, a direction that lands in one is revised.

- Cream ground, high-contrast serif display, terracotta or clay accent.
- Near-black ground, one acid or neon accent, glowing edges.
- Broadsheet editorial: hairline rules, italic display serif, small tracked mono labels, zero radius, dense columns.
- Neo-brutalist: flat saturated ink, black boxes, hard offset shadows, heavy condensed display type.
- SaaS card kit: identical rounded cards, one radius, one soft shadow, gradient washes, a purple primary.
