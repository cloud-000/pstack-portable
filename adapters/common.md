# pstack portability rules

This guide translates the upstream Cursor vocabulary used in this skill and its supporting files. Apply these translations before following an upstream instruction. The session's system/developer instructions and the user's explicit choices take precedence over this guide and the upstream workflow.

## Routing and package paths

The package root is two levels above this skill's directory (`skills/<name>`). Resolve the skill directory's real path first if it was discovered through a symlink. Read another packaged skill through `<package-root>/skills/<name>/SKILL.md` and its harness guide. Do not search Cursor caches, fetch GitHub main, or choose a different installed release. If a required local skill is absent, report that dependency as unavailable rather than loading an inactive cached version. Relative links in upstream files are preserved where possible.

Read `<package-root>/agent-profiles/poteto-agent.md` or `comment-sicko.md` for the corresponding delegate's brief. These are prompt resources, not registered host agent types. Include the profile and the absolute active poteto-mode path in the delegate's initial brief; do not pass these names as a native agent type unless the current session explicitly offers them.

## Model configuration

Before a model-dependent step, read `~/.config/pstack-portable/@HARNESS@/models.json` if it exists. Its `roles` mapping overrides upstream role defaults. A role value is an object `{ "model": "inherit-parent" }` or a list of such objects for a panel, optionally with a supported `effort`. Use only models/efforts exposed by the actual tool schema or an available entitlement API. Upstream `grok-*`, `claude-*`, `composer-*`, and `gpt-*` slugs are historical Cursor defaults, not evidence that this harness supports them. With no configuration, inherit the current session's model and disclose that diverse-model coverage is unavailable unless distinct models can actually be selected.

Never substitute a user-selected model, provider, reasoning setting, or speed silently. If unavailable, report the limitation. A same-model panel is not an independent multi-model review. If diversity is required by the user or is essential to the selected workflow's acceptance condition, stop that step as BLOCKED. Do not represent sequential work as parallel execution or a local worktree as a cloud machine.

## Runtime capabilities

- `Task`, `generalPurpose`, `subagent_type`, `run_in_background`, `resume`, `file_attachments`, `cloud_base_branch`, and `environment` describe Cursor's delegation API. Use the host mapping below and only fields present in the actual schema. Honor the session's delegation authorization and concurrency limits. If delegation is unavailable, perform only work whose acceptance conditions permit a single agent; report independent review as missing.
- `readonly: true` means a read-only brief, and a genuinely read-only host sandbox when available. A prompt alone is not a security boundary. `environment: "cloud"` needs isolation for concurrent writes; use a host-supported isolated workspace when available and report the distinction from remote execution.
- `AskQuestion` means the available structured user-input tool, or a concise text question when absent. A timeout is not consent. A todo list means the host plan tool, or a short maintained task list if none is available.
- `Grep`, `Glob`, `Read`, and `Bash` mean the equivalent available file/search/shell tools. Prefer `rg` for text searches. Never call a tool based only on an upstream name.
- `/loop`, Cursor custom modes, wakeups, Cursor Automations, `update_state`, `SendToUser`, and Cursor webhook APIs have no assumed equivalent. Do not install a scheduler or external integration as an implicit fallback. If optional, note the omission. If needed for the promised result, mark the step BLOCKED.
- Bugbot review comments already present on a PR can be read through an available forge integration. Starting or waiting for Bugbot requires a configured integration; do not fabricate checks. Use available forge tools for PR work within the user's authorization.
- The `cursor-team-kit` skills (`deslop`, `control-ui`, `control-cli`) and Cursor's `create-skill` are external dependencies, not bundled skills. Use an explicitly available equivalent for the same purpose and identify it. If unavailable, perform a direct review or verification only when it satisfies the acceptance condition; otherwise report the gap.
- For `.cursor/rules/*.mdc` or always-applied rule writes, use an appropriate host instruction file only for an expressly requested persistent rule. Do not overwrite unrelated instructions. Model configuration belongs only in the JSON file above, read explicitly by these adapters.
- For `.cursor/skills/` writes, use this harness's supported skill location and distinguish project from global scope. For Cursor transcript paths, use only a host-provided history/search capability scoped to the user's requested project. Never guess another harness's private transcript layout.
- A skill marked explicit-only must not be automatically selected merely because its description matches. When routed deliberately by another invoked pstack workflow, follow the host's invocation policy. Do not turn pstack on persistently for unrelated tasks.

## Compatibility limits

These adaptations preserve the engineering procedures, not every Cursor platform feature. The release's compatibility report records exclusions and static checks. A passing build is not proof of runtime model availability, native skill discovery, cloud orchestration, or independent review. State missing evidence plainly.
