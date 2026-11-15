# Design conventions, latitude and AI defaults by product category

Researched 2026-11-15 from primary guidelines, NN/g, Baymard, award juries and the sites themselves. Basis for a design skill that must look made, not generated, without breaking what each category's users rely on. Figures carry their source date; pages that could not be read (Apple's HIG change log, m3.material.io, Siteinspire, Godly) are named.

## Cross-category references

- WCAG 2.2 is the current Recommendation: first published October 2023, current edition [12 December 2024](https://www.w3.org/TR/WCAG22/). New at A/AA: 2.4.11 Focus Not Obscured (AA), 2.5.7 Dragging Movements (AA), 2.5.8 Target Size Minimum (AA), 3.2.6 Consistent Help (A), 3.3.7 Redundant Entry (A), 3.3.8 Accessible Authentication Minimum (AA); 4.1.1 Parsing was removed. 2.5.8 asks for [24 by 24 CSS px](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html), with spacing, equivalent, inline, user-agent and essential exceptions.
- WCAG 3.0 is still a Working Draft; the latest W3C-listed draft is [3 March 2026](https://www.w3.org/TR/2026/WD-wcag-3.0-20260303/), and W3C says it [does not replace WCAG 2](https://www.w3.org/WAI/WCAG3). A claimed September 2026 draft is not on w3.org. Design to 2.2 AA.
- Core Web Vitals: LCP at most 2.5 s, INP at most 200 ms, CLS at most 0.1, judged at the 75th percentile of page loads, mobile and desktop separately ([web.dev](https://web.dev/articles/vitals), updated 2024-10-31).
- Apple Human Interface Guidelines: the live pages (read through the JSON behind [Materials](https://developer.apple.com/design/human-interface-guidelines/materials)) are written around Liquid Glass, introduced at WWDC 2025 with the OS 26 releases. I could not open the HIG change log, so changes for the 27 releases are unverified.
- Material 3 Expressive: announced 13 May 2025, shipped on Pixel with Android 16 QPR1 on [3 September 2025](https://9to5google.com/2025/09/03/android-16-qpr1-pixel/). The research write-up is [Google Design's article](https://design.google/library/expressive-material-design-google-research): 46 studies, more than 18,000 participants. m3.material.io renders client-side and could not be read; component names below come from secondary sources.
- Microsoft Fluent 2: launched June 2023; the [What's new page](https://fluent2.microsoft.design/get-started/whatisnew) carries no dated entries, so there is no version to pin.
- Vercel Web Interface Guidelines: a living checklist at [vercel.com/design/guidelines](https://vercel.com/design/guidelines), source in [vercel-labs/web-interface-guidelines](https://github.com/vercel-labs/web-interface-guidelines) (MIT, last commit 2026-10-05). The most agent-ready list here: 24 px hit targets (44 px on mobile), `:focus-visible` rings, 16 px mobile input font, never block paste or zoom, state in the URL, reduced-motion variants, animate only `transform` and `opacity`.
- NN/g 10 usability heuristics: 1994, [last reviewed 2024-01-30](https://www.nngroup.com/articles/ten-usability-heuristics/). Number 4, consistency and standards, sets how far a design may stray from category convention.
- Refactoring UI ([refactoringui.com](https://refactoringui.com/)): hierarchy through size, weight and colour together; design a feature before a layout.
- Licences: W3C document licence for WCAG; Vercel's guidelines are MIT; Apple's HIG and Refactoring UI are copyrighted, so summarise, never copy. Material's documentation licence not checked.

## Generic AI defaults (all categories)

Two sources describe the same shared look. [prg.sh (2025-10-26)](https://prg.sh/ramblings/Why-Your-AI-Keeps-Building-the-Same-Purple-Gradient-Website) lists Inter or Roboto, indigo or purple gradients on white, a centred hero with one CTA, a three-column grid of icon cards, soft rounded corners, faint shadows and stock fade-ins, and traces the purple to Tailwind UI's `indigo-500` placeholder. [Adrian Krebs (2026-04-20)](https://adriankrebs.ch/blog/design-slop/) scored about 1,590 Show HN landing pages with deterministic DOM and computed-style checks: 22% showed four or more markers and 32% two or three. His markers add Space Grotesk / Instrument Serif / Geist pairings, a serif italic accent word in the hero, permanent dark mode with low-contrast body text, all-caps section labels, coloured glows, a badge above the H1, coloured card edge borders, numbered steps, stat banners, emoji icons, shadcn/ui defaults and glassmorphism (5-10% false positives by his manual QA). Banning one tell moves output to the next most probable one, so the skill should steer toward category- and brand-specific choices, not only forbid.

## Brochure site for a local or small business (sito vetrina)

Job: answer "is this the place, is it open, where is it, how do I book or call" in one screen, and show the place so people want to go.

Conventions users rely on:
- Menu or services, hours, address with map link, phone and booking one tap from the homepage. In a [Menufy 2026](https://restaurant.menufy.com/article/5-things-costing-your-restaurant-orders) survey 59% had given up ordering because they could not find menu, hours or ordering options (vendor data, indicative). No NN/g study of restaurant sites turned up.
- Menus in HTML, not PDF; `tel:` links; booking through the platform the business already uses (TheFork, OpenTable, Tock); hours matching the Google Business Profile.
- `LocalBusiness` / `Restaurant` structured data: `name` and `address` required; `geo`, `openingHoursSpecification`, `telephone`, `menu`, `servesCuisine`, `priceRange` recommended ([Google Search Central](https://developers.google.com/search/docs/appearance/structured-data/local-business)).
- Italian legal floor: the partita IVA on the homepage (art. 35 DPR 633/1972, carried into the 2026 Testo unico IVA; fines from 250 to 2,000 euros), even for a purely promotional site ([diritto.it](https://www.diritto.it/l-indicazione-della-partita-iva-sul-sito-web-e-obbligatoria/)); a cookie banner where an X closes it with only technical cookies and scrolling is not consent ([Garante 2021 guidelines, via iubenda](https://www.iubenda.com/it/help/31246-italy-new-cookie-rules)).

Latitude: photography (the place, people, product; never stock), type and colour taken from the physical identity (sign, menu card, shop front), story sections, tone of copy. The practical block may look like anything as long as it is text in a predictable place.

Decoration budget: medium imagery, low motion, medium type risk: real photos carry the page, a characterful display face suits headings, motion stays at reveal-on-scroll. Example: [noma.dk](https://noma.dk/), large editorial photos and a plain wordmark, with hours, address and a "Book a table" link to Tock in plain text.

Floors: LCP is usually the hero photo (sized AVIF/WebP, `fetchpriority="high"`, no autoplay video hero on mobile); 1.4.3 contrast for text over photos; 2.5.8 for phone and map links; 1.1.1 alt text on dish and room photos; a text address beside any map iframe.

AI defaults in this category: a full-bleed stock photo with a centred "Welcome to [Name]" and "Experience the finest..." copy, three icon cards ("Fresh ingredients", "Cosy atmosphere", "Friendly staff"), a fake testimonial carousel, hours missing or buried in the footer, the generic SaaS palette applied to a trattoria.

## SaaS / product marketing site

Job: explain what the product does for whom, prove it, and route visitors to signup, pricing, docs or sales.

Conventions users rely on:
- Top nav with Product, Pricing, Docs (or Developers), Customers, Log in at the right, and a primary CTA. Stripe's current homepage follows this exactly ([stripe.com](https://stripe.com/), read 2026-11-15).
- A pricing page that shows numbers. NN/g reports that business buyers rate [price as their top information need](https://www.nngroup.com/articles/show-price/) and that complex pricing is no excuse; for configurable products, [show prices for common scenarios](https://www.nngroup.com/articles/show-prices-for-common-scenarios/). Plans in columns, a feature comparison table, an FAQ, an annual/monthly toggle.
- A real product screenshot or live demo above the fold, customer logos, a changelog link, a docs entry with search (usually Cmd/Ctrl+K).
- Links are links (`<a>`, middle-click works), and locale-aware prices with consistent decimals ([Vercel guidelines](https://vercel.com/design/guidelines)).

Latitude: the hero visual (how the product is shown: cropped UI, interactive component, illustration system), type pairing, colour commitment, section rhythm, voice. Ordering of proof sections is free.

Decoration budget: medium to high on the homepage, low on pricing and docs. Examples: [linear.app](https://linear.app/), real issue screens and changelog entries doing the work of illustration; [stripe.com](https://stripe.com/), the gradient wave plus a product bento and hard numbers (uptime, volume processed). Awwwards' SaaS category has few recent Site of the Day winners; juries reward experiments over conversion pages.

Floors: INP on interactive heroes (WebGL, scroll-linked animation); CLS from late fonts and cookie bars; 2.2.2 pause for logo marquees and loops over five seconds; 1.4.3 for grey-on-dark hero copy; 2.4.7 focus on the pricing toggle and plan buttons.

AI defaults in this category: the Krebs list fits best here: badge over a centred H1, gradient text, "Supercharge your workflow", three identical feature cards, a numbered "How it works" row, invented stats, an abstract blob instead of the product, placeholder "Trusted by" logos, three tiers with the middle one "Most popular".

## SaaS product UI: dashboards, admin, data-dense tools

Job: let people find, compare and act on records quickly, all day, without the interface getting in the way.

Conventions users rely on:
- A persistent left sidebar, a top bar with search or command palette, page titles that say where you are, account in a corner.
- Tables built for tasks: sticky headers, a human-readable first column, discoverable filters with a visible active state, sort on any column, at most one or two inline row actions with the rest in a labelled menu, batch actions with select-all, side panels rather than modals for editing ([NN/g data tables, 2022](https://www.nngroup.com/articles/data-tables/)).
- Density as a setting: Carbon offers row heights of 24, 32, 40, 48 and 64 px, header and pagination matching the row height ([Carbon data table](https://carbondesignsystem.com/components/data-table/style)).
- Charts: bars, lines and scatter for quantities; colour for categories, not magnitude; no 3D; bullet charts instead of radial gauges; pie only for overwhelming disparities ([NN/g preattentive dashboards](https://www.nngroup.com/articles/dashboards-preattentive/)).
- State in the URL (filters, tabs, pagination), undo or confirmation for destructive actions, optimistic updates that roll back on failure ([Vercel guidelines](https://vercel.com/design/guidelines)).

Latitude: the neutral palette and its single accent, type (a good grotesk or a mono for figures, tabular numerals), iconography, empty states and onboarding illustration, micro-interactions on success. Linear's [March 2026 refresh](https://linear.app/changelog/2026-03-12-ui-refresh) is a model of where effort goes: consistent headers and view controls across object types, redrawn icons, a dimmer sidebar so content wins.

Decoration budget: low. Motion only to explain state change, colour reserved for status and selection, no decorative imagery in working views.

Floors: 1.4.11 non-text contrast (3:1) for input borders, focus rings, chart lines; 1.4.1 status carries an icon or label, not only red/green; 2.1.1 keyboard for every table action; 2.4.11 focus not hidden under sticky headers; 2.5.8 for dense icon buttons, with 4.1.2 names on them; 1.4.10 reflow (scrolling inside a table is allowed). INP matters more than LCP: virtualise long lists, do not re-render the table per keystroke.

AI defaults in this category: four KPI cards with delta and sparkline, a gradient-filled area chart, a donut, a "Recent activity" list, rounded white shadowed cards on grey, indigo on every link, hover-only row icons, "Welcome back, John", no empty, loading or error states.

## Mobile app (iOS and Android)

Job: do one set of tasks well with the thumb, in short sessions, and feel native.

Conventions users rely on (iOS, from the HIG JSON read 2026-11-15):
- Tab bar for navigation only, never actions; always visible except under a modal; labels on tabs, filled SF Symbols, avoid the More overflow, never hide or disable a tab ([Tab bars](https://developer.apple.com/design/human-interface-guidelines/tab-bars)).
- Liquid Glass is for the control and navigation layer that floats above content, not for content itself; use it sparingly on custom controls; the clear variant only over rich media, with a 35% dimming layer when the media is bright; standard materials (ultra-thin to thick) stay in the content layer ([Materials](https://developer.apple.com/design/human-interface-guidelines/materials)). Extend full-screen content under bars and use scroll-edge effects instead of solid bar backgrounds ([Layout](https://developer.apple.com/design/human-interface-guidelines/layout)).
- Dynamic Type to at least 200% text size; controls 44x44 pt by default and 28x28 pt at minimum on iOS, with about 12 pt padding around bezelled controls; contrast 4.5:1 up to 17 pt text; respect Reduce Motion by tightening springs and replacing x/y/z transitions with fades ([Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility)).

Conventions on Android:
- Edge-to-edge is enforced for apps targeting SDK 35 on Android 15 and later; handle system-bar, cutout and gesture insets ([Android developers](https://developer.android.com/develop/ui/views/layout/edge-to-edge)).
- Touch targets of at least 48x48 dp with 8 dp spacing ([Android accessibility help](https://support.google.com/accessibility/android/answer/7101858)).
- M3 Expressive adds button groups, FAB menu, loading indicator, split button, floating toolbars and a spring-based motion scheme set in the theme ([proandroiddev summary](https://proandroiddev.com/android-16-x-material-3-e-biggest-ui-change-yet-updates-for-android-jetpack-compose-and-flutter-35d6b53a5242)); several Compose APIs were `material3` 1.5.0 alphas, so check stability.

Latitude: Google's research draws the line. Expressive shape, colour, size and motion let users spot key actions up to four times faster, but scattered album art and unlabelled email actions tested worse, banking should keep established patterns, and a strong minority preferred calmer versions: "No amount of emotion can compensate for a lack of clarity" ([Google Design](https://design.google/library/expressive-material-design-google-research)). Free: brand colour (dynamic colour on Android), illustration, onboarding, empty states, emphasis on the one key action per screen, haptics. Linear's iOS app built its own glass that also runs on iOS 18, skipped refraction to keep dense lists legible, and adds outlines under Increase Contrast ([Linear, 2025-10-21](https://linear.app/blog/linear-liquid-glass)).

Decoration budget: system-led: system springs, imagery inside content, type risk only in display moments, glass only on controls. Examples: Apple Design Award 2026 winners [Tide Guide](https://www.apple.com/newsroom/2026/06/apple-reveals-winners-of-the-2026-apple-design-awards/) (Visuals and Graphics, a tide charts and tables app) and Moonlitt (Interaction); 2025 winners [Watch Duty and CapWords](https://9to5mac.com/2025/06/03/apple-announces-2025-apple-design-award-winners/).

Floors: platform defaults (44 pt, 48 dp) exceed 2.5.8; text scaling to 200% without truncation (1.4.4 analogue); 2.5.7 a tap alternative to every swipe or drag; 1.3.4 orientation not locked without reason; Reduce Transparency and Increase Contrast honoured when glass is custom.

AI defaults in this category: a web page in a phone frame: hamburger instead of tab bar, unlabelled five-icon bottom bars, glass blur on every card, a centred hero with gradient CTA, iOS chevrons on Android or FABs on iOS, fixed font sizes, no safe-area insets.

## E-commerce (listing, product page, cart, checkout)

Job: help people find the right product, trust the price and the shop, and pay without friction.

Conventions users rely on (Baymard Institute):
- Listings: the five essential filters (price, rating, colour, size, brand) and four essential sorts (price, rating, best-selling, newest); 51% and 69% of large sites miss them; show applied filters; merge colour variants into one list item; show unit price ([Baymard PLP, 2025-09-09](https://baymard.com/research-articles/current-state-product-list-and-filtering)).
- Product page: sizes as buttons, not a drop-down (57% fail); in-scale and on-model images; return policy and estimated total cost near the buy button (about 60% look for returns there); unit price; browsable review images ([Baymard PDP, 2026-03-18](https://baymard.com/research-articles/current-state-ecommerce-product-page-ux)).
- Checkout: guest checkout always, account offered after the order; mark required and optional fields; say why a phone number is needed (68% are reluctant); a delivery date, not a shipping speed; completed steps collapsed into summaries ([Baymard checkout, 2026-11-03](https://baymard.com/research-articles/current-state-of-checkout-ux)).
- The average US checkout shows 23.48 form elements against an ideal of 12-14; documented cart abandonment averages 70.22% over 50 studies; extra costs (40%), slow delivery (20%), distrust with card details (19%) and forced accounts (18%) lead the reasons ([Baymard, 2026-10-28](https://baymard.com/lists/cart-abandonment-rate)).

Latitude: the brand layer (homepage, campaigns, editorial, photography, type of product names) and storytelling below the buy box. Buy box, filters, cart and checkout should look like every other shop. Example: [Scout Motors](https://locomotive.ca/en/work/scout-motors), Awwwards E-commerce of the Year in the 2025 [annual awards](https://www.awwwards.com/annual-awards/winners), an immersive brand site for a revived off-road maker (the case study says little about the purchase flow itself).

Decoration budget: high on brand pages, near zero from cart onward. Imagery is product photography, and plenty of it; motion limited to image zoom and add-to-cart feedback.

Floors: LCP is the main product image (carousels must not load every slide); CLS from late price, badge and review widgets; INP on filter toggles. WCAG: 3.3.1 and 3.3.3 errors identified and explained; 1.3.5 `autocomplete` tokens; 3.3.7 shipping reused as billing; 3.3.8 no puzzle CAPTCHA, paste and password managers allowed; 2.5.8 for steppers and swatches; 1.4.1 swatches carry names. In the EU, the European Accessibility Act has applied to e-commerce services since 28 June 2025; microenterprises providing services are exempt, but the exact boundary is disputed between sources ([Taylor Wessing](https://www.taylorwessing.com/en/interface/2025/accessibility/key-eu-accessibility-act-exemptions-and-the-challenges-they-pose)); check Directive 2019/882 itself.

AI defaults in this category: a hero banner with "Discover our collection", identical product cards with a heart icon and a "Shop now" button, a size drop-down, fake urgency ("Only 2 left!", countdown timers), invented star ratings, a centred newsletter pop-up on load, a multi-step checkout that asks for an account first, no unit price or delivery date.

## Portfolio, editorial and campaign (brand-led) sites

Job: carry a point of view; the site itself is often the work sample.

Conventions users rely on:
- A way to reach the work quickly (index or grid), a clear name and discipline, contact details that are copyable text, a visible way out of any immersive section.
- Native scrolling: NN/g found [scrolljacking](https://www.nngroup.com/articles/scrolljacking-101/) hurts control, discoverability and efficiency, worst when it changes speed or direction on pages people must read.
- For editorial: readable measure (roughly 45-75 characters), a byline and date, working back navigation, shareable URLs per story.

Latitude: almost everything visual: grid, expressive type, colour, WebGL, sound, cursor work, transitions. The 2025 Awwwards annual winners show the ceiling: [Lando Norris by OFF+BRAND.](https://www.awwwards.com/sites/lando-norris) (Site of the Year: acid yellow on near-black, 3D and gesture-driven), [Messenger by abeto](https://www.awwwards.com/sites/messenger) (Developer Site of the Year: a tiny Three.js planet, multiplayer over WebSockets, where you make deliveries), Immersive Garden (Agency of the Year), Louis Paquet (Independent of the Year).

Decoration budget: high, but spent on one idea. In Awwwards' reviews Lando Norris scored 8.71 for creativity and 7.00 for accessibility, Messenger 9.00 for animation and 7.60 for accessibility: even the best work here pays for spectacle in accessibility, and a skill should close that gap.

Floors: 2.3.1 three flashes at most; 2.2.2 pause for autoplaying motion and video; `prefers-reduced-motion` gets a real static version (2.3.3 is AAA, but the setting is the user's request); 2.4.3 focus survives page transitions; 1.4.5 text in the DOM, not only canvas; loaders must not hold LCP back, and a WebGL hero needs a fast poster frame.

AI defaults in this category: a centred oversized name with a serif italic word, a marquee strip of skills, a bento grid of project cards with hover zoom, a custom cursor dot, smooth-scroll library on every page, "Let's work together" in giant type at the bottom, gradient mesh or grain backgrounds, case studies without the problem, the role or the outcome.

## How the categories differ

- Convention weight runs from checkout and product UI (highest) through mobile (platform-led) and local business (practical block fixed, the rest free) to SaaS marketing and brand-led sites (lowest).
- The generic defaults cross every category; the worst cases come from applying the SaaS landing template where other conventions rule: a trattoria, a checkout, an iOS app.
