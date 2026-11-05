## Codex mapping

- User-facing invocation is `$<skill-name>` in Codex CLI/IDE. Upstream `/name` references identify the corresponding packaged skill; read its active local file when the session lacks a skill invocation tool.
- Prefer the session's supported delegation facility. If it exposes `spawn_agent`, use its real schema, pass a standalone brief, and collect completion with the corresponding wait/result facility. If a surrounding application defines a different orchestration interface, follow that application's instructions. Do not assume background, model-selection, isolation, or resume fields exist on `spawn_agent`.
- Use `update_plan` for task plans when available. Use an available request-user-input tool within its supported mode; otherwise ask in text.
- Codex global skill discovery uses `~/.agents/skills/`; repository skill discovery uses `.agents/skills/`. The latter is shared with other harnesses, so do not put a harness-specific variant there when both harnesses will read it.
- Upstream `disable-model-invocation: true` is translated into `agents/openai.yaml` with `policy.allow_implicit_invocation: false`. Host enforcement, rather than this prose, controls implicit discovery.
- Cursor `icon` and `color` names are omitted from Codex frontmatter. Cursor `paths` globs are preserved as file-scope guidance in the skill body, not represented as a native Codex trigger.

References: https://learn.chatgpt.com/docs/build-skills
