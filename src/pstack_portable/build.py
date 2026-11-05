"""Deterministic upstream import and harness-specific release compilation."""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import posixpath
import re
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlsplit


UPSTREAM = "https://github.com/cursor/plugins.git"
TARGETS = ("codex", "antigravity")
EXCLUDED = {"make-bot-ui": "Requires Grok Bot / Cursor automation webhook infrastructure; no equivalent backend is bundled."}
TEMPLATE_LINKS = {("skills/why/references/synthesizer-prompt.md", "url")}
LINK = re.compile(r"(?<!!)\[[^\]\n]+\]\(([^)\s]+)\)")


class Error(Exception):
    pass


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def inventory(root):
    result = {}
    for path in sorted(Path(root).rglob("*")):
        if path.is_symlink():
            raise Error(f"Source symlinks are unsupported: {path}")
        if path.is_file():
            result[path.relative_to(root).as_posix()] = {
                "sha256": sha(path.read_bytes()),
                "executable": bool(path.stat().st_mode & 0o111),
            }
    return result


def read_json(path):
    return json.loads(Path(path).read_text())


def changed(before, after):
    return {"added": sorted(set(after) - set(before)), "removed": sorted(set(before) - set(after)),
            "modified": sorted(k for k in set(before) & set(after) if before[k] != after[k])}


def git(cache, *args):
    return subprocess.check_output(["git", "-C", str(cache), *args], text=True).strip()


def sync(project, ref="main", offline=False):
    project = Path(project)
    cache = project / ".upstream-cache"
    if ref.startswith("-"):
        raise Error("Invalid upstream ref")
    if not cache.exists():
        if offline:
            raise Error("No upstream cache for offline sync")
        subprocess.run(["git", "clone", "--no-checkout", "--depth=1", UPSTREAM, str(cache)], check=True)
    if git(cache, "remote", "get-url", "origin") != UPSTREAM:
        raise Error("Upstream cache origin differs from the configured repository")
    if not offline:
        git(cache, "fetch", "--depth=1", "origin", ref)
        commit = git(cache, "rev-parse", "FETCH_HEAD")
    else:
        commit = git(cache, "rev-parse", ref if ref != "main" else "HEAD")
    archive = subprocess.check_output(["git", "-C", str(cache), "archive", commit, "pstack"])
    previous = read_json(project / "upstream.lock") if (project / "upstream.lock").exists() else {}
    with tempfile.TemporaryDirectory(dir=project) as tmp:
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            if any(not (m.isfile() or m.isdir()) for m in tar.getmembers()):
                raise Error("Upstream contains non-regular files")
            tar.extractall(tmp, filter="data")
        source = Path(tmp) / "pstack"
        files = inventory(source)
        lock = {"schemaVersion": 1, "repository": UPSTREAM, "ref": ref, "commit": commit,
                "subdirectory": "pstack", "version": read_json(source / "plugin.json")["version"], "files": files}
        report = {"previousCommit": previous.get("commit"), "commit": commit, **changed(previous.get("files", {}), files)}
        dest = project / "upstream/pstack"
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            if previous and inventory(dest) != previous["files"]:
                raise Error("Vendored upstream has local modifications; refusing to overwrite")
            shutil.rmtree(dest)
        shutil.copytree(source, dest)
        (project / "upstream.lock").write_bytes(canonical(lock))
        (project / "sync-report.json").write_bytes(canonical(report))
    return report


def check_source(project):
    lock = read_json(project / "upstream.lock")
    if inventory(project / "upstream/pstack") != lock["files"]:
        raise Error("Vendored source differs from upstream.lock; restore it or run sync")
    return lock


def review(project, accept=False):
    lock = check_source(project)
    path = project / "reviewed-inputs.json"
    prior = read_json(path).get("files", {}) if path.exists() else {}
    result = changed(prior, lock["files"])
    if accept:
        path.write_bytes(canonical({"commit": lock["commit"], "files": lock["files"]}))
    return result


def frontmatter(text):
    m = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    if not m:
        raise Error("Skill has no supported YAML frontmatter")
    name = re.search(r"^name:\s*(.+)$", m[1], re.M)
    if not name or not re.search(r"^description:\s*\S", m[1], re.M):
        raise Error("Skill requires name and description")
    return name[1].strip().strip("\"'"), m[0], text[m.end():]


def rewrite_links(text, relative_path, source, output, commit):
    def replace(match):
        href = match[1]
        parsed = urlsplit(href)
        if parsed.scheme or href.startswith("#"):
            # Pin upstream main links to this artifact's exact source revision.
            return match[0].replace("github.com/cursor/plugins/blob/main/pstack/", f"github.com/cursor/plugins/blob/{commit}/pstack/")
        dest = posixpath.normpath(posixpath.join(posixpath.dirname(relative_path), unquote(parsed.path)))
        if dest.startswith("../") or dest.startswith("/"):
            raise Error(f"Link leaves plugin: {relative_path} -> {href}")
        if dest.startswith("agents/"):
            renamed = "agent-profiles/" + dest[len("agents/"):]
            link = posixpath.relpath(renamed, posixpath.dirname(relative_path))
            return match[0].replace(href, link + ("#" + parsed.fragment if parsed.fragment else ""))
        if (output / dest).exists():
            return match[0]
        if (source / dest).exists():
            kind = "tree" if (source / dest).is_dir() else "blob"
            url = f"https://github.com/cursor/plugins/{kind}/{commit}/pstack/{dest}"
            return match[0].replace(href, url + ("#" + parsed.fragment if parsed.fragment else ""))
        # Upstream contains examples/templates whose Markdown destinations are placeholders.
        # Record these in link-report instead of pretending they resolve.
        return match[0]
    return LINK.sub(replace, text)


def source_roles(source):
    text = (source / "skills/setup-pstack/SKILL.md").read_text()
    block = re.search(r"# budget:.*?\n(.*?)\n```", text, re.S)
    if not block:
        raise Error("setup-pstack role block changed; update the targeted setup adapter")
    roles = []
    for line in block[1].splitlines():
        name, sep, _ = line.partition(":")
        if sep:
            roles.append(name)
    if not roles:
        raise Error("No model roles found")
    return roles


def build(project, output=None, candidate=False):
    project = Path(project).resolve()
    lock = check_source(project)
    delta = review(project)
    if any(delta.values()) and not candidate:
        raise Error("Upstream has unreviewed changes; inspect review/sync-report, update adapters, then record review --accept. Use --candidate only for inspection.")
    source = project / "upstream/pstack"
    adapter_inputs = {"adapters/" + p: v for p, v in inventory(project / "adapters").items()}
    adapter_inputs.update({"src/" + p: v for p, v in inventory(project / "src").items() if "__pycache__" not in p})
    revision = sha(canonical(adapter_inputs))
    version = f"{lock['version']}+portable.1.{lock['commit'][:8]}.{revision[:8]}"
    manifest = {"schemaVersion": 1, "id": "pstack-portable", "version": version,
                "status": "candidate" if candidate else "reviewed",
                "provenance": {"repository": UPSTREAM, "subdirectory": "pstack", "commit": lock["commit"], "adapterRevision": revision},
                "variants": {}}
    report = {"upstreamCommit": lock["commit"], "upstreamVersion": lock["version"], "adapterRevision": revision,
              "excludedSkills": EXCLUDED, "runtimeVerified": False,
              "externalDependencies": ["cursor-team-kit/deslop", "cursor-team-kit/control-ui", "cursor-team-kit/control-cli"],
              "capabilityGates": ["delegation", "model-selection", "independent-multi-model-review", "cloud-orchestration", "persistent-scheduling", "bugbot"],
              "variants": {}}
    output = Path(output).resolve() if output else project / "dist/bundle"
    if output == project or output in project.parents or output == source or source in output.parents:
        raise Error("Output must not replace the project or upstream source")
    # Only replace directories produced by this builder.
    if output.exists() and not (output / "bundle.json").is_file():
        raise Error(f"Output exists and is not a generated bundle: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".pstack-build-") as tmp:
        root = Path(tmp) / "bundle"
        roles = source_roles(source)
        for target in TARGETS:
            base = root / "bundles" / target
            base.mkdir(parents=True)
            for directory in ("skills", "docs"):
                shutil.copytree(source / directory, base / directory)
            shutil.copytree(source / "agents", base / "agent-profiles")
            for name in EXCLUDED:
                if (base / "skills" / name).exists():
                    shutil.rmtree(base / "skills" / name)
            for name in ("README.md", "LICENSE"):
                shutil.copy2(source / name, base / name)
            readme = base / "README.md"
            invocation = "$setup-pstack" if target == "codex" else "/setup-pstack"
            readme.write_text(
                f"# pstack-portable for {target}\n\n"
                f"Adapted from upstream commit `{lock['commit']}`. Start with `{invocation}` after installing this variant. "
                "Keep the complete package layout when installing skill directories. "
                "Each skill links to its harness guide, which translates Cursor tools, paths and model defaults. "
                "The upstream README below is retained as reference; its Cursor installation commands and platform-specific promises do not apply to this variant. "
                "See the accompanying compatibility-report.json for exclusions and runtime limitations.\n\n---\n\n"
                + readme.read_text())
            native = {"$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json", "name": "pstack-portable", "version": version,
                      "description": f"pstack engineering skills adapted for {target}", "license": "MIT", "author": {"name": "pstack-portable contributors (upstream pstack by Lauren Tan)"}}
            if target == "antigravity":
                native["$schema"] = "https://antigravity.google/schemas/v1/plugin.json"
            (base / "plugin.json").write_bytes(canonical(native))
            guide = (project / "adapters/common.md").read_text() + "\n" + (project / f"adapters/{target}.md").read_text()
            guide = guide.replace("@HARNESS@", target)
            names = sorted(p.name for p in (base / "skills").iterdir() if (p / "SKILL.md").is_file())
            rules = []
            for name in names:
                path = base / "skills" / name / "SKILL.md"
                text = path.read_text()
                parsed_name, front, body = frontmatter(text)
                if parsed_name != name:
                    raise Error(f"Skill name/folder mismatch: {name}")
                explicit = bool(re.search(r"^disable-model-invocation:\s*true\s*$", front, re.M))
                translated_fields = []
                scope = None
                if target == "codex":
                    translated_fields = re.findall(r"^(disable-model-invocation|icon|color|paths):", front, re.M)
                    scoped = re.search(r"^paths:\s*(.+)$", front, re.M)
                    scope = scoped[1] if scoped else None
                    front = re.sub(r"^disable-model-invocation:.*\n", "", front, flags=re.M)
                    front = re.sub(r"^(?:icon|color|paths):.*\n", "", front, flags=re.M)
                preamble = "\nBefore following this workflow, read [the pstack harness guide](references/pstack-harness.md). It translates the Cursor vocabulary below for this harness.\n"
                if explicit:
                    preamble += "Use this workflow only when explicitly invoked or deliberately routed by an invoked workflow; do not select it from description matching alone.\n"
                if scope:
                    preamble += f"The upstream file scope is `{scope}`. Apply these rules to files matching that scope; this is guidance, not a host-enforced glob trigger.\n"
                if name == "setup-pstack":
                    body = (project / "adapters/setup-pstack.md").read_text().replace("@HARNESS@", target).replace("@ROLES@", "\n".join("- `" + role + "`" for role in roles))
                    front = re.sub(r"^description:.*$", "description: Configure available models and reasoning settings for pstack roles in this harness. Use when asked to set up pstack or change its model preferences.", front, flags=re.M)
                path.write_text(front + preamble + "\n" + body)
                refs = path.parent / "references"
                refs.mkdir(exist_ok=True)
                (refs / "pstack-harness.md").write_text(guide)
                if target == "codex" and explicit:
                    metadata = path.parent / "agents/openai.yaml"
                    if metadata.exists():
                        raise Error(f"Upstream now includes Codex metadata for {name}; merge policy explicitly")
                    metadata.parent.mkdir(exist_ok=True)
                    metadata.write_text("policy:\n  allow_implicit_invocation: false\n")
                rules.append({"skill": name, "explicitOnly": explicit, "adaptation": "setup-replacement" if name == "setup-pstack" else "harness-guide", "translatedFrontmatter": translated_fields})
            for path in sorted(base.rglob("*.md")):
                rel = path.relative_to(base).as_posix()
                path.write_text(rewrite_links(path.read_text(), rel, source, base, lock["commit"]))
            shared = []
            for p in sorted(base.iterdir()):
                if p.name != "skills":
                    shared.append({"id": "resource:" + re.sub(r"[^a-z0-9]+", "-", p.name.lower()).strip("-"), "kind": "resource", "path": p.name, "requires": []})
            components = list(shared)
            unresolved = []
            for name in names:
                deps = {c["id"] for c in shared}
                for p in (base / "skills" / name).rglob("*.md"):
                    # Deliberate routes and relative cross-skill links are dependencies.
                    text = p.read_text()
                    for other in names:
                        if other != name and (re.search(r"`/" + re.escape(other) + r"`|\*\*" + re.escape(other) + r"\*\*", text) or re.search(r"\.\./" + re.escape(other) + r"/", text)):
                            deps.add("skill:" + other)
                    for match in LINK.finditer(text):
                        href = match[1]
                        if urlsplit(href).scheme or href.startswith("#"):
                            continue
                        resolved = p.parent / unquote(urlsplit(href).path)
                        if not resolved.exists():
                            rel = p.relative_to(base).as_posix()
                            if (rel, href) not in TEMPLATE_LINKS:
                                raise Error(f"Unresolved skill reference: {rel} -> {href}")
                            unresolved.append({"file": rel, "link": href, "reason": "upstream citation-template placeholder"})
                components.append({"id": "skill:" + name, "kind": "skill", "path": f"skills/{name}", "requires": sorted(deps)})
            manifest["variants"][target] = {"root": f"bundles/{target}", "components": components, "files": inventory(base),
                                           "compatibility": {"discovery": "global-skill-directories", "runtimeVerified": False}}
            report["variants"][target] = {"skills": rules, "unresolvedUpstreamLinks": unresolved}
        (root / "bundle.json").write_bytes(canonical(manifest))
        (root / "compatibility-report.json").write_bytes(canonical(report))
        if output.exists():
            shutil.rmtree(output)
        shutil.move(root, output)
    return {"version": version, "output": str(output), "upstreamCommit": lock["commit"], "status": manifest["status"]}


def package(bundle, archive):
    bundle, archive = Path(bundle), Path(archive)
    archive.parent.mkdir(parents=True, exist_ok=True)
    with archive.open("wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz, tarfile.open(fileobj=gz, mode="w") as tar:
        for p in sorted(bundle.rglob("*")):
            if p.is_symlink():
                raise Error("Cannot package symlinks")
            info = tar.gettarinfo(str(p), arcname=p.relative_to(bundle).as_posix())
            info.uid = info.gid = info.mtime = 0
            info.uname = info.gname = ""
            info.mode = 0o755 if p.is_dir() or p.stat().st_mode & 0o111 else 0o644
            if p.is_file():
                with p.open("rb") as f:
                    tar.addfile(info, f)
            else:
                tar.addfile(info)
    checksum = sha(archive.read_bytes())
    Path(str(archive) + ".sha256").write_text(f"{checksum}  {archive.name}\n")
    return {"archive": str(archive), "sha256": checksum}
