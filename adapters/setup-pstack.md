# Setup pstack for @HARNESS@

Read [the harness guide](references/pstack-harness.md) first.

Configure pstack's model roles in `~/.config/pstack-portable/@HARNESS@/models.json`. This file is explicitly read by pstack's adapters; it is not a host rule or an always-applied instruction.

1. Read the current JSON if present. Discover selectable models and reasoning settings from this session's actual delegation schema or an available entitlement API. Never infer model access from upstream Cursor defaults. If the harness cannot select models, explain that limitation and use `inherit-parent` as the available choice.
2. Ask for the user's desired reasoning budget and model roles, preserving choices they already supplied. Explain whether diverse-model review is possible. Use only supported reasoning levels; do not infer an effort setting from a model's name.
3. Propose a role mapping. The supported upstream roles for this release are listed below. An individual role is an object with `model` and optional `effort`. Panel roles use an array of these objects. `inherit-parent` means omit a model override. Do not include secrets, provider credentials, or unsupported settings.
4. Write the selected configuration as valid JSON with `schemaVersion: 1`, `harness: "@HARNESS@"`, and a `roles` object. Preserve unrelated existing roles unless they are explicitly being removed. Validate the written file by parsing it. Report its path and any limitations. No write to AGENTS.md, GEMINI.md, or Cursor rules is required.
5. If the user also wants a project verification workflow, route to the packaged create-verification-skill or create-formal-verification-skill as appropriate. Do not create one merely to finish model setup.

## Roles from the pinned upstream setup skill

@ROLES@
