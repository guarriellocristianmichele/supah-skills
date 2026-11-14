# slop-guard ships the hooks as a separate opt-in plugin that carries a copy of the scanner

Rules against slop are injected by hooks, not by a skill, because a skill loads only when the model reaches for it. The hooks live in their own plugin, `plugins/slop-guard`, listed in the marketplace as `slop-guard`: plugin hooks start on install, and people who installed the bundle for the skills did not ask for context in every session. The plugin stays cheap. `SessionStart` prints a rule file of about 150 tokens. `PostToolUse` scans only the text just written to a prose file, so text a person wrote earlier is never flagged. It stays silent when that text is clean and otherwise sends one line on stderr with exit 2 (the documented way to show a message to Claude after a tool has run). The rules apply to code and files, never to chat replies.

## Considered options

- Hooks in the bundle (`hooks/hooks.json` at the repo root): rejected; every bundle user would get them without asking.
- A marketplace entry with `source: "./"`: rejected; it shares the root `plugin.json`, so its hooks would merge into the bundle.
- Referencing `skills/ai-slop-prose/scripts` from the plugin: impossible; an installed plugin is copied to the cache without files outside its folder. A symlink would break on Windows checkouts (`core.symlinks=false`), so `scanner/` is a copy kept equal by `scripts/release.py`.
- A `UserPromptSubmit` reminder on every prompt: rejected for its per-prompt token cost.
- Scanning code on write: added later with the code scanner (ADR 0010); it reads the saved file, because an edit alone often does not parse, and keeps the hits on the new lines.

## Consequences

- After any change to `skills/ai-slop-prose/scripts` or `skills/ai-slop-audit/scripts` (rules, lexicons, calibration), run `python scripts/release.py --sync`; `--check` fails until the copies match.
- skills.sh does not install hooks, so slop-guard is a Claude Code plugin only.
