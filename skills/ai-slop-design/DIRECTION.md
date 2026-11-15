# Direction

How craft turns a subject into a direction. The lanes a direction must stay out of are in `REFLEXES.md`.

## Where distinct choices come from

The subject's world: its materials, its places, its tools, its vernacular, the objects its people handle. A bicycle workshop has enamel paint, chrome, grease-stained paper tickets and stencilled frame numbers; a tax adviser has carbon-copy forms, rubber stamps and archive boxes. Palette, type and layout borrow from those objects. A direction that could be pasted onto another subject unchanged came from the category, not the subject.

## Scene sentence

One sentence: who uses the page, where, under what light, in what mood. "A commuter checking opening hours on a phone at a bus stop in the rain" settles light versus dark, the type size and what goes first; "a professional services website" settles nothing. Add detail until the sentence decides the theme.

## Voice words

Three words naming physical objects or materials ("enamel, receipt, cast iron"), never qualities ("modern, clean, premium"). Every later choice answers to them.

## Palette

- Name 4 to 6 colours by role and by what they come from ("ticket buff", "frame-number red"), in OKLCH.
- Pick a strategy before the hues:
  - **restrained**: tinted neutrals plus one accent on about a tenth of the surface;
  - **committed**: one saturated colour carries a third to a half;
  - **full**: three or four roles, each used on purpose;
  - **drenched**: the surface is the colour.
- Tint every neutral toward the palette's hue; lower chroma as lightness nears 0 or 100.
- Text passes 4.5:1 against its background, 3:1 when large.

## Font procedure

1. From the voice words, describe the face as an object: "the lettering on a 1960s enamel sign", "a typewritten repair ticket".
2. Write the three faces you would reach for first. Any of them on the reflex-font list (REFLEXES.md) is set aside, and so is any face used in `.slop-design/history.md`.
3. Search a real catalogue (Google Fonts, Fontshare, Velvetyne, Collletttivo, a foundry's specimen pages) for the object, not for "elegant serif" or "modern sans"; with the browser the user allowed, open it and read the specimen at display and body sizes.
4. Check the pick against step 2. If it matches a first reach, start again from step 1 with a different object.
5. Set a scale with steps at least 1.25 apart, body line length 60 to 75 characters, and weights that differ visibly.

One family can be enough; two must differ clearly in role.

## Layout

Write the concept in one sentence ("the page reads like a repair ticket: the job, the price, the pickup time"), then an ASCII wireframe of the first two screens at desktop and at 390 pixels. The order of sections follows what the visitor needs first, not the landing-page template. Space varies with the content's rhythm; equal gaps everywhere flatten it.

## Responsive

Design the phone first and let wider screens add room; the direction must hold at every width, not only look right at 1440.

- Breakpoints come from the content: add one where the layout breaks, not at a device list. Container queries for components that live in different widths.
- Type scales with `clamp()`; body text is at least 16 pixels on phones, line length stays at 60 to 75 characters on wide screens.
- No horizontal scroll from 320 pixels up; wide content (tables, code, carousels) scrolls inside its own box.
- Touch targets at least 24 by 24 pixels with space between them (44 on iOS-style controls); every hover effect has a touch and focus equivalent.
- Images carry `srcset` and `sizes`, keep their aspect ratio (`aspect-ratio` or width and height attributes) so nothing jumps, and the hero image is art-directed for the phone crop when the subject sits off-centre.
- Fixed and sticky bars respect `env(safe-area-inset-*)` and leave the content readable in landscape.
- The memorable element survives the phone: when it cannot, the phone gets its own version of it, not a shrunken one.

Responsive checks for the look step: at 390, 768 and 1440 pixels, no horizontal scroll, nothing clipped or overlapping, tap targets usable, text readable without zoom, the primary action visible without hunting, and the memorable element still memorable.

## Memorable element

One place where boldness is spent: an oversized word, a single photograph, an interactive object, a typographic move. Everything around it stays quiet. When two elements compete, cut one.

## Motion

One moment, or none: a load sequence, a reveal tied to the content, or feedback that answers an action. Ease out with exponential curves; animate transform and opacity only.

## Imagery

When the subject is visual (food, places, products, people, craft), the page shows it. Prefer the project's own assets; otherwise verified stock searched by the subject's objects ("chrome lugs on a steel frame"), or a generated scene. Coloured boxes standing in for photographs are a bug. Alt text says what the image shows, in the page's voice.

## Quality floor

Responsive down to 390 pixels, visible keyboard focus, motion behind `prefers-reduced-motion`, text contrast as in Palette, real links and buttons, content readable without JavaScript.
