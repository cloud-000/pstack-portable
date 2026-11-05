# pstack-portable

Reproducible pstack adaptations for Codex and Antigravity, built from the canonical
[`cursor/plugins/pstack`](https://github.com/cursor/plugins/tree/main/pstack)
source. Python 3.11.8+, Git, and no Python runtime dependencies.

This project owns upstream synchronization, pstack-specific adaptations,
compatibility review, and artifact creation. It does not install skills or manage
harness activation. [skillsctl](../../../utils/skillsctl/README.md) consumes the
generic bundle contract, but is not imported or required to build this project.

## Build and use

```sh
./bin/pstack-portable build
./bin/pstack-portable package

skillsctl install ./dist/bundle --harness codex --harness antigravity
```

The checked-in snapshot and lock make `build` entirely offline. `bin/pstack-portable`
finds this checkout even when invoked from another directory. A pip-installed CLI
uses the current directory, or `pstack-portable --project /path/to/checkout ...`.

Outputs:

```text
dist/bundle/bundle.json                  generic lifecycle contract
dist/bundle/compatibility-report.json    exclusions, mappings, and static evidence
dist/bundle/bundles/codex/               native plugin/skill tree
dist/bundle/bundles/antigravity/          native plugin/skill tree
dist/pstack-portable.tar.gz              reproducible archive
dist/pstack-portable.tar.gz.sha256       archive integrity digest
```

The release identity combines upstream's version and commit with a digest of the
adapter and builder sources. Rebuilding identical inputs yields identical trees
and archives. A changed adaptation produces a different identity even when the
upstream version is unchanged. Upstream licenses are retained in every variant.

## Updating upstream

```sh
./bin/pstack-portable sync
./bin/pstack-portable review
./bin/pstack-portable build --candidate --output ./dist/candidate
```

`sync` resolves upstream `main` to an exact commit and updates the pristine vendored
tree, `upstream.lock`, and `sync-report.json`. `--ref <sha-or-ref>` can pin a specific
revision. A `.upstream-cache` Git checkout is only a download cache. Locally modified
vendored content is never silently overwritten. An interrupted import causes the
lock/inventory checks to fail; restore the snapshot from Git before retrying.

Review the source diff, model/tool assumptions, new external dependencies,
invocation policies, and unresolved links. Adapt `adapters/` or the targeted
transforms when needed. Then record that review and build:

```sh
./bin/pstack-portable review --accept
PYTHONPATH=src python3 -m unittest discover -s tests -v
./bin/pstack-portable build
./bin/pstack-portable package
skillsctl update pstack-portable --harness codex --harness antigravity
```

`review --accept` records your review; it does not perform one. A normal build
refuses any unreviewed upstream file change. Candidate builds remain marked
`candidate` and skillsctl refuses to install them. The original upstream tree is
never edited by an adaptation. Commit the lock, snapshot, review record, adapter
changes, and report together.

“Latest” for installations means the latest reviewed artifact. The report always
shows its exact upstream commit; it does not claim that unreviewed upstream changes
are already supported.

## Adaptation strategy

- Preserve upstream skills, scripts, guide documents, and relative layout.
- Add a maintained harness guide to each skill with tool, routing, model, path,
  and unsupported-capability mappings. Supporting upstream documents retain
  Cursor vocabulary interpreted through that guide.
- Replace only the setup-pstack implementation with a harness-specific JSON
  configuration workflow. The builder extracts the pinned upstream role names;
  a changed role-block format fails the build.
- Translate Codex explicit-only invocation metadata into `agents/openai.yaml`.
- Keep upstream delegate profiles as `agent-profiles/` resources; adapters use
  them in native delegate briefs rather than claiming they are registered agents.
- Rewrite links to omitted upstream files to the pinned commit, never moving main.
- Declare local skill references as component dependencies. Shared resources are
  required at the same release, so pstack's dependency cohorts are conservative.

User instructions and host orchestration rules take precedence. Model availability
is discovered at runtime; a Cursor model slug is never assumed to work elsewhere.
Model-role settings live in `~/.config/pstack-portable/<harness>/models.json` and
are read explicitly, without changing global host instructions.

## Compatibility and validation

The current snapshot emits 57 skills per target. `make-bot-ui` is excluded because
it requires external bot/webhook infrastructure. Cursor cloud agents, persistent
loops, Automations, and Bugbot control are capability-gated. `cursor-team-kit`
is not bundled. Optional unavailable steps are disclosed; a missing capability
needed for acceptance blocks the step rather than fabricating completion.

Antigravity native validation:

```sh
agy plugin validate dist/bundle/bundles/antigravity --strict --json
```

This validates metadata/loading, not the behavioral quality of workflows. The
release report deliberately retains `runtimeVerified: false` until actual host
sessions are exercised. Antigravity's enforcement of explicit-only invocation
must be checked on the chosen surface; the adapter preserves upstream metadata
and adds a routing instruction. A same-model panel is not multi-model review.

Tests:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 scripts/integration_check.py --skillsctl ~/CodeProjects/utils/skillsctl
```

The integration check uses a temporary home and runs real CLI validation,
installation, activation, update, rollback, and integrity checks on both targets.
It does not use your live credentials or change your actual harness setup.

## Manual installation without skillsctl

Keep a complete generated variant at a stable path outside a discovery directory.
Symlink each `skills/<name>` directory into the target global skill directory:
`~/.agents/skills/` for Codex or `~/.gemini/config/skills/` for Antigravity. Keep the
package tree intact so sibling skills and shared references resolve. Check for
existing names before linking. Native plugin installers can also consume the
generated plugin trees; use only one installation method to avoid duplicate skills.

Do not put both variants in the shared workspace `.agents/skills` directory.
Reload/start a new session after changing installed content.

## CI and releases

The test workflow checks deterministic output and unit tests. The scheduled sync
workflow opens an upstream-import PR and uploads a candidate; it leaves an existing
review branch untouched and never
accepts its own compatibility review. Enable Actions with write/PR permissions
after publishing this repository. Push a release tag only after reviewing and
testing; the release workflow builds and attaches an immutable tarball and digest.
No remote repository or release is created by local setup.
