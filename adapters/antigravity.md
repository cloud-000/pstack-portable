## Antigravity mapping

- User-facing invocation is `/<skill-name>`. Resolve cross-skill instructions to the active local package, not to Cursor's plugin cache.
- On surfaces exposing `invoke_subagent`, use its current schema. Use an available `define_subagent` facility or a normal delegate brief for packaged agent profiles. A suitable documented built-in role may be `self` or `research`, but only pass a role the current session offers.
- Antigravity App/CLI documentation describes workspace choices `inherit`, `branch`, and `share`, and model tiers such as `inherit`, `flash`, and `pro`. Inspect the session's actual tool definitions before use; these are not Cursor model slugs and are not guaranteed on every IDE surface. Use isolated workspaces for overlapping writes, and collect real terminal results.
- Use the host's available planning/task interface and question interface. Do not invent a `Task` or `AskQuestion` tool when neither is present.
- Global skills use `~/.gemini/config/skills/`; workspace skills use `.agents/skills/`. Keep this variant out of a shared workspace discovery directory when Codex also uses that workspace.
- This bundle preserves upstream explicit-only metadata and adds an explicit invocation instruction. Exact implicit-invocation enforcement varies by Antigravity surface; verify it in the installed version before relying on it.

References: https://antigravity.google/docs/skills?app=antigravity-ide and https://antigravity.google/docs/subagents
