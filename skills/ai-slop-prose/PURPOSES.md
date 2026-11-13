# Purposes

A rewrite serves what the text is for. The scanner reports a `purpose` per hit: from the tag, attribute, key or call around a string in a source file, or from `--purpose` for a whole document. Rewrite to the purpose's job; every TELLS.md fix still applies. Keep the language of the text: the examples give English and Italian.

## Interface text

| Purpose | Its job | Rewrite to | Before → after |
|---|---|---|---|
| `button` | name the action the click performs | verb + object, ≤ 3 words, no punctuation | "Click here to get started!" → "Create account"; "Scopri di più!" → "Vedi i prezzi" |
| `link` | say where it goes | the destination, never "click here" / "clicca qui" | "Click here" → "Pricing plans"; "Clicca qui" → "Tariffe" |
| `label` | name the field or control | a noun phrase, sentence case | "Your Amazing Email" → "Email"; "Inserisci La Tua Email" → "Email" |
| `placeholder` | show an example of the expected input | a sample value, never the instruction the label already gives | "Enter your email address" → "name@example.com"; "Inserisci il tuo nome" → "Mario Rossi" |
| `alt` | describe what the image shows for someone who cannot see it | what matters in the picture; empty for decoration; no "image of" | "Image of a happy team" → "Four people reviewing a whiteboard plan"; "Immagine del logo" → "Logo Pasticceria Rossi" |
| `tooltip`, `hint` | add the one fact the label cannot hold | one short sentence | "This is where the magic happens" → "Visible only to admins"; "Qui avviene la magia" → "Visibile solo agli amministratori" |
| `heading`, `title`, `tab`, `menu` | name the section | the subject, sentence case, no slogan | "Unlock the Full Potential of Your Data" → "Data export"; "Nel mondo frenetico di oggi, il tuo carrello" → "Carrello" |
| `error` | say what happened, why, and what to do | fact, cause if known, next step; no apology theatre, no blame | "Oops! Something went wrong. Don't worry!" → "Payment declined. Check the card details or use another card."; "Certo! Ecco cosa è successo: il pagamento non è andato a buon fine." → "Pagamento rifiutato. Controlla i dati della carta o usane un'altra." |
| `message` | confirm what changed | past tense, the object, the consequence if any | "Awesome! You're all set!" → "Settings saved"; "Fantastico, è tutto pronto!" → "Impostazioni salvate" |
| `empty-state` | explain why it is empty and the first action | one line of state, one action | "It's lonely here…" → "No invoices yet. Create your first invoice."; "Il tuo carrello è vuoto." stays: it already does the job |
| `onboarding` | get the user to the first useful step | the step, the benefit in plain words | "Embark on your journey" → "Import your contacts to start"; "Inizia il tuo viaggio" → "Importa i contatti per iniziare" |
| `meta` | match the search query and the page | what the page offers, ≤ 155 characters, no superlatives | "Not just a shop, it's an experience" → "Handmade pastries in Modena, delivered the same day"; "Non è solo un negozio, è un'esperienza." → "Pasticceria artigianale a Modena, consegna in giornata." |
| `email` | one request or one piece of news | the point in the first line; subject = the point | "I hope this email finds you well" → straight to the request; "Spero che tu stia bene" → la richiesta |
| `i18n`, `string` | unknown from code | infer from the key, the screen and nearby strings; ask when unclear | |

On microcopy (`button`, `link`, `label`, `placeholder`, `alt`, `tooltip`, `hint`, `heading`, `title`, `option`, `tab`, `menu`) the scanner already skips rhythm and Title Case rules, since "Save. Cancel." is a toolbar, not a fragment run. Keep a product's established capitalisation and terminology: a glossary or style guide in the repo wins over these defaults.

## Whole documents (`--purpose`)

| Purpose | Its job | Rewrite to |
|---|---|---|
| landing page, product page | show what it does and for whom, then the next step | concrete outcomes, numbers, one call to action; cut stakes inflation and "revolutionary" |
| docs, README | let the reader do the task | the task first, commands and expected output, then reference; cut meta-text about the document |
| blog post, article | argue one point well | the point early, evidence, the author's voice; cut signposted endings |
| email, newsletter | one action or one piece of news per message | the point in the first sentence, the ask stated once |
| release notes, changelog | what changed for the user | one line per change, user-facing effect first |
| legal, terms, privacy | precision | keep defined terms and hedges that carry legal meaning; fix only residue, punctuation and typos |
| support reply | solve the user's problem | the answer, the steps, one line of empathy at most |
| social post | one idea in the platform's voice | the idea first; keep hashtags and emoji only if the brand uses them |
