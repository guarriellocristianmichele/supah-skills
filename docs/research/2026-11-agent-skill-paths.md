# Where agents load skills from, and how they install them

Researched 2026-11-13 from official docs and source code. Basis for the install routes in the root README. Agents rename and move folders often; re-check before changing an install command.

## Skill directories

| Agent | Project | Global | Reads `.agents/skills`? | Source |
|---|---|---|---|---|
| Claude Code | `.claude/skills/` (nested too), plugin `skills/` | `~/.claude/skills/` | no | [docs](https://code.claude.com/docs/en/skills) |
| Codex CLI | `.agents/skills` (cwd up to repo root), `.codex/skills` | `~/.agents/skills`; `$CODEX_HOME/skills` deprecated but read; `/etc/codex/skills` | yes | [docs](https://learn.chatgpt.com/docs/build-skills), `codex-rs/ext/skills/src/host_roots.rs` |
| Copilot CLI | `.github/skills`, `.agents/skills`, `.claude/skills` | `~/.copilot/skills`, `~/.agents/skills`, `COPILOT_SKILLS_DIRS` | yes | [docs](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-plugin-reference) |
| VS Code (Copilot) | `.github/skills/`, `.claude/skills`, `.agents/skills` | `~/.copilot/skills/`, `~/.claude/skills/`, `~/.agents/skills/` | yes | [docs](https://code.visualstudio.com/docs/copilot/customization/agent-skills) |
| Gemini CLI | `.gemini/skills/` or `.agents/skills/` (`.agents` wins) | `~/.gemini/skills/` or `~/.agents/skills/` | yes | [docs](https://geminicli.com/docs/cli/skills/) |
| Cursor | `.agents/skills/`, `.cursor/skills/`, `.claude/skills`, `.codex/skills` | same under `~` | yes | [docs](https://cursor.com/docs/context/skills) |
| OpenCode | `.opencode/skills`, `.claude/skills`, `.agents/skills` | `~/.config/opencode/skills`, `~/.claude/skills`, `~/.agents/skills` | yes | [docs](https://opencode.ai/docs/skills/) |
| Devin Desktop (ex Windsurf) | `.devin/skills/`, `.agents/skills/`, legacy `.windsurf/skills/` | `~/.config/devin/skills/`, `~/.agents/skills/` | yes | [docs](https://docs.devin.ai/desktop/cascade/skills) |
| Amp | `.agents/skills/`, `.claude/skills/` | `~/.config/agents/skills/`, `~/.agents/skills/`, `~/.config/amp/skills/`, `~/.claude/skills/` | yes | [docs](https://ampcode.com/docs/customize/skills) |
| Goose | `.agents/skills/`, legacy `.goose/skills/`, `.claude/skills/` | `~/.agents/skills/`, `~/.claude/skills/` | yes | [docs](https://goose-docs.ai/docs/guides/context-engineering/using-skills) |
| Cline | `.cline/skills/`, `.clinerules/skills/`, `.claude/skills/` | `~/.cline/skills/` | not documented | [docs](https://docs.cline.bot/features/skills) |
| Roo Code | `.roo/skills/`, `.agents/skills/` | `~/.roo/skills/`, `~/.agents/skills/` | yes | [docs](https://roocodeinc.github.io/Roo-Code/features/skills) |
| Kiro | `.kiro/skills/` | `~/.kiro/skills/` | no | [docs](https://kiro.dev/docs/skills/) |
| Junie CLI | `.junie/skills/`, `.agents/skills/` | `~/.junie/skills/`, `~/.agents/skills/` | yes | [docs](https://junie.jetbrains.com/docs/agent-skills.html) |
| Pi | `.pi/skills/`, `.agents/skills/` | `~/.pi/agent/skills/`, `~/.agents/skills/` | yes | pi-mono `packages/coding-agent/docs/skills.md` |
| Factory Droid | `.factory/skills/`, `.agents/skills/` | `~/.factory/skills/`, `~/.agents/skills/` | yes | [docs](https://docs.factory.com/cli/configuration/skills) |
| Qwen Code | `.qwen/skills/`, `.agents/skills/` | `~/.qwen/skills/`, `~/.agents/skills/` | yes | [docs](https://qwenlm.github.io/qwen-code-docs/en/users/features/skills/) |
| Continue | `.continue/skills`, `.claude/skills` | `~/.continue/skills` | no | `extensions/cli/src/util/loadMarkdownSkills.ts` |
| Aider | none | none | no native skills | — |

Gemini CLI was replaced by Antigravity CLI on 2026-06-18 for unpaid and Google One accounts ([Gemini CLI docs](https://geminicli.com/docs/cli/skills/)).

## skills.sh (`npx skills`, vercel-labs/skills 1.8.1)

Verified in the package source (`dist/_chunks/remove.mjs`, `dist/cli.mjs`) and with `npx skills@latest add guarriellocristianmichele/supah-skills --list`, which listed all three skills.

- `add` with no `-g` and no `-y` prompts **"Installation scope"**: *Project* ("Install in current directory (committed with your project)") or *Global* ("Install in home directory (available across all projects)"). `update` prompts "Update scope"; `-g` or `-p` answers it.
- Flags: `-g/--global`, `-a/--agent`, `-s/--skill` (`'*'` for all), `-l/--list`, `-y/--yes`, `--copy`, `--all`, `--json`.
- Default install keeps one copy in `.agents/skills/<name>` (or `~/.agents/skills` with `-g`) and symlinks each agent's folder to it; falls back to copying when symlinks fail. A local path source is copied.
- Agent ids include `claude-code`, `codex`, `github-copilot`, `gemini-cli`, `cursor`, `opencode`, `windsurf`, `amp`, `goose`, `cline`, `roo`, `kiro-cli`, `junie`, `pi`, `droid`, `qwen-code`, `continue`, `antigravity`.
- Its own path table disagrees with some agents' docs (Cline, Windsurf/Devin, Goose); the agents' docs above take precedence.

## Plugin marketplaces

| Agent | Commands | Scope | Verified |
|---|---|---|---|
| Claude Code | `claude plugin marketplace add <owner/repo> [--scope user\|project\|local]`; `claude plugin install <plugin>@<marketplace> [-s user\|project\|local]`; one step: `claude plugin install <plugin> --marketplace <owner/repo>` | CLI does not prompt; default `user` | `--help` output; local-scope test installs of `ai-slop-prose` (1 skill) and `supah-skills` (3 skills) |
| Codex | `codex plugin marketplace add <owner/repo>`; install from the app's Plugins Directory (mattpocock/skills documents `codex plugin add` on 0.161) | user | docs only |
| Copilot CLI | `copilot plugin marketplace add <owner/repo>`; `copilot plugin install <plugin>@<marketplace>` | user | docs only |
| Gemini CLI | `gemini skills install <git-url> [--path <subdir>] [--scope user\|workspace]` | flag | docs only |

Codex and Copilot CLI both read `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`.

## Frontmatter portability

- claude.ai and the Skills API reject any key besides `name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools`.
- Claude Code ignores unknown keys. Codex and Gemini CLI read only `name` and `description` (Codex also `metadata.short-description`) and ignore the rest.
- `disable-model-invocation` is honoured by Cursor, OpenCode, Pi, Factory, Qwen Code and VS Code.
- Only Claude Code substitutes `$ARGUMENTS` and `${CLAUDE_SKILL_DIR}` and runs `` !`cmd` `` injection. Pi and Factory append the user's text instead; Qwen Code reads `allowedTools`, not `allowed-tools`.

## Not verified

Unknown-key handling in Copilot CLI, Cursor, OpenCode, Kiro, Devin, Junie, Factory, Goose and Roo; `codex plugin install` syntax; whether Claude Code will read `.agents/skills`; Kiro and `~/.agents/skills`; Antigravity CLI's own paths; a single-skill Gemini install with `--path skills/<name>`.
