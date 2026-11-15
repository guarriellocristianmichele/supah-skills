# Categories

What kind of thing is being built sets how far a page may go. Read the section for each surface in scope; a SaaS product has two (its marketing site and its product UI), a shop's brand pages and its checkout are two as well.

Each section has five parts:

- **Frame**: conventions visitors rely on. Keep them; creativity that breaks the frame costs usability, and the page reads as a puzzle rather than a choice.
- **Room**: where the direction is free to go far.
- **Accessory budget**: how much decoration (motion, imagery, type risk, colour commitment) the category carries. Premium means every accessory earns its place; spend the budget on the memorable element and keep the rest quiet.
- **Floor**: the accessibility and performance checks that bite hardest in this category, on top of DIRECTION.md's quality floor.
- **Category reflexes**: what generated work in this category converges on, beyond REFLEXES.md.

Sources, dates and the evidence behind each line: `docs/research/2026-11-design-categories.md` in the supah-skills repository.

## Local business site

A restaurant, studio, shop or professional practice.

- Frame: menu or services, opening hours, address with a map link, a phone number as a `tel:` link and booking, each one tap from the homepage. Menus and price lists in HTML, never only as a PDF. Hours that match the business's map listing. `LocalBusiness` structured data. In Italy, the VAT number (partita IVA) on the site and a cookie banner whose close button refuses.
- Room: the business's own photography, a type and palette taken from its physical identity (the sign, the menu card, the shop front, the uniforms), the tone of the copy.
- Accessory budget: medium imagery, low motion, medium type risk. One decisive photograph beats a carousel.
- Floor: the hero photo is the LCP element, so size and preload it; text over photos keeps its contrast with a scrim or a solid band; phone and map links are at least 24 by 24 pixels; alt text describes the dish or the room.
- Category reflexes: a stock hero with "Welcome to …", three icon cards for services, invented testimonials, hours hidden in the footer.

## SaaS marketing site

Landing page, pricing, the doorway to the docs.

- Frame: a nav with product, pricing, docs and sign-in, plus one primary call to action; real prices on the pricing page; a real product screenshot or live demo above the fold; a changelog and searchable docs one click away.
- Room: how the product is shown in the hero (a live demo, a short loop, one large real screen), the type pairing, how committed the colour is, the rhythm of sections.
- Accessory budget: medium to high on the homepage, low on pricing and docs, where clarity wins.
- Floor: interactive heroes stay responsive (INP ≤ 200 ms); late fonts and cookie bars cause no layout shift (CLS ≤ 0.1); moving logo strips and marquees have a pause control; the monthly and yearly pricing toggle is keyboard-reachable with visible focus.
- Category reflexes: a pill badge above a centred headline, Inter with an indigo gradient, three icon cards, invented usage numbers, three plans with the middle one marked "most popular".

## SaaS product UI

Dashboards, admin panels, data-dense tools.

- Frame: a persistent sidebar or top nav, a command palette or search, tables with sticky headers, a readable first column, filters in view and one or two row actions; detail in a side panel rather than a modal; a density setting; state in the URL so views can be shared; bar and line charts before gauges, donuts or 3D.
- Room: a neutral palette with one accent, figure typography (tabular numbers), icon style, empty states and first-run screens.
- Accessory budget: low. Motion only to show what changed; colour only to carry meaning.
- Floor: non-text contrast 3:1 for controls and chart marks; status shown by more than colour; every action reachable by keyboard; focus never hidden under sticky headers; long lists virtualised so input stays responsive.
- Category reflexes: KPI cards with sparklines across the top, a gradient area chart, a donut, white cards with soft shadows, "Welcome back" headers.

## Mobile app

iOS and Android.

- Frame: the platform's navigation (a labelled tab bar on iOS, a navigation bar or rail on Android), the platform's own controls and gestures, system text sizes up to the largest accessibility size, touch targets of 44 points on iOS and 48 dp on Android, edge-to-edge layout on current Android. On iOS, translucent "glass" materials belong to the control layer (bars, toolbars, sheets), never to content.
- Room: brand colour, illustration, onboarding, haptics, and emphasis on the one key action of a screen. Expressive emphasis helps when the basic patterns stay where people expect them.
- Accessory budget: set by the platform; use its springs, materials and transitions before inventing new ones.
- Floor: every gesture has a tap alternative; text scales without clipping; custom translucent surfaces honour reduced transparency and increased contrast; motion honours reduced motion.
- Category reflexes: a web page inside a phone frame, a hamburger menu, glass on every card, iOS and Android idioms mixed on one screen.

## E-commerce

Product listing, product page, cart, checkout.

- Frame: the filters and sorts shoppers expect for the category; sizes as buttons, not a drop-down; product images that show scale; price, delivery date, returns and total cost next to the buy button; guest checkout; the shortest checkout the business allows (aim for about a dozen form fields).
- Room: the brand layer: campaign pages, the story below the buy box, photography and art direction.
- Accessory budget: high on brand and campaign pages, close to zero from the cart onward.
- Floor: the product image is the LCP element; review and chat widgets cause no layout shift; form fields carry `autocomplete` tokens; nothing already entered is asked for twice; sign-in needs no memory test. In the EU, the European Accessibility Act applies to most online shops.
- Category reflexes: "Discover our collection" heroes, a size drop-down, fake urgency timers, invented ratings, an account wall before checkout.

## Portfolio, editorial and campaign

Studios, personal portfolios, long-form stories, launches.

- Frame: a fast route to the work, contact details that can be copied, native scrolling, readable line length, a URL for each project or story.
- Room: almost everything visual: type, layout, art direction per section, ambitious first-load motion.
- Accessory budget: high, spent on one idea. Award-winning work in this category often scores poorly on accessibility; the floor below is what keeps ambition usable.
- Floor: no content that flashes more than three times a second; moving or auto-playing content can be paused; a real reduced-motion version; focus kept across page transitions; text present in the DOM, not only in canvas or images.
- Category reflexes: an oversized name with one serif italic word, a skills marquee, a bento grid of tools, a custom cursor dot, smooth scrolling everywhere, "Let's work together" as the closing line.
