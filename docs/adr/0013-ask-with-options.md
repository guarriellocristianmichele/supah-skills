# Skills settle doubts by looking first, and ask the user with ready answers

Every skill carries the same paragraph, **Ask with options**: a doubt is settled first by looking (the repository, its docs, and a web search when the answer is a fact about the world); what only the user can decide is asked as one question with 2 to 4 ready answers, the recommended one first, each saying what it changes. In Claude Code the `AskUserQuestion` tool shows the question and its answers on screen; other agents number the answers in the reply.

A question with ready answers costs the user one choice instead of a paragraph, makes the trade-off visible, and lets the recommended path go ahead with one keystroke. Looking first keeps questions for decisions that are the user's: brand, audience, which side of a contradiction wins, whether an issue leaves the machine.

## Considered options

- Open questions only: rejected; the user has to invent the options the agent already knows.
- One shared file every skill points at: rejected; per-skill installs cannot reach files outside their folder (ADR 0008, ADR 0012), so the paragraph is repeated in each SKILL.md, worded identically.
- Asking before looking: rejected; a question the repository answers wastes the user's turn.

## Consequences

- A new skill copies the paragraph verbatim after its placeholder line; changing the wording means changing it in every SKILL.md.
- Steps that already wait for the user (publishing issues, approving context-audit's fix list, running a test command) phrase their question the same way.
