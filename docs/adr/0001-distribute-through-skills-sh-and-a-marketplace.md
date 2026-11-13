# Distribute through skills.sh and a plugin marketplace, not our own installer

Skills install through `npx skills add guarriellocristianmichele/supah-skills` for every agent, and through the `guarriellocristianmichele` plugin marketplace (`.claude-plugin/`) for Claude Code, Codex and Copilot CLI. We dropped a hand-written Python install wizard: skills.sh already knows every agent's folders, prompts for the scope, and updates itself, while our own installer would need re-checking every time an agent moves a directory. The marketplace lists the full `supah-skills` bundle plus one plugin per skill, and `skills/` stays flat (no category buckets), because Codex accepts a single skills path per plugin.

## Consequences

- The scope is prompted only by skills.sh; the Claude Code CLI takes `--scope` and defaults to `user`, so the README gives the command for each scope.
- Installing the bundle and a single-skill plugin together loads that skill twice; the README says to pick one.
- Hook plugins that are not skills live in `plugins/<name>` with their own manifest and have no skills.sh route (ADR 0008).
- `version` lives in `plugin.json` and in each single-skill marketplace entry; `scripts/release.py` keeps them equal.
