# The prose scanner finds every catalogued tell; the model judges each hit

ai-slop-prose pairs a deterministic scanner with model judgement instead of asking the model to "write more naturally". The scanner guarantees that every pattern in its catalogue is found and reported with an exit code; the model rewrites or keeps each hit with a reason, and reads for the tells no regex can see. "Complete" therefore means "no catalogued tell remains", never "written by a person": the research (Wikipedia, Kobak et al., Graphite) is clear that these signs are statistical and that detection of authorship is unreliable.

## Considered options

- Model-only rewriting (as in humanizer): rejected, because nothing proves a category was checked, and rewrites swap one tic for another.
- Flag em dashes by density only, as the 2026 research suggests (recent models rarely use them): rejected at the user's request; every em dash is an M-tier hit, removable or kept with a reason.
