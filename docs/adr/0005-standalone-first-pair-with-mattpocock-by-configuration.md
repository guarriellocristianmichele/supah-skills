# Standalone first; pair with mattpocock/skills through their configuration

Every skill works without mattpocock/skills. When a repo has run `/setup-matt-pocock-skills` (detected by `docs/agents/issue-tracker.md`), ai-slop-audit reads that tracker and label configuration, hands design work to `/improve-codebase-architecture`, and adds `code-review` to `verify`. We read their files and invoke their skills, but we never copy their formats (our issues use our own template, not their Agent Brief) and never write their reserved paths (`docs/agents/`, `.scratch/`, `.out-of-scope/`). This keeps the two sets from drifting into each other and lets either be upgraded alone.

## Consequences

- Our own repo follows their file conventions (`GLOSSARY.md`, `docs/adr/NNNN-slug.md`, a minimal `CLAUDE.md` their setup can extend), so their skills work here too.
- A batch built by `/implement` is synced from the tracker, never rebuilt by `fix`.
