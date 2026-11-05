import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pstack_portable.build import Error, build, canonical, inventory, package, review


def fixture(project):
    source = project / "upstream/pstack"
    for name in ("alpha", "beta", "setup-pstack", "make-bot-ui"):
        directory = source / "skills" / name
        directory.mkdir(parents=True)
        content = "Read [beta](../beta/SKILL.md).\n" if name == "alpha" else "A standalone workflow.\n"
        if name == "setup-pstack":
            content = "```\n# budget: large (xhigh)\nworker: cursor-model\n```\n"
        (directory / "SKILL.md").write_text(f"---\nname: {name}\ndescription: Do {name}\ndisable-model-invocation: true\n---\n# {name}\n{content}")
        if name == "alpha":
            script = directory / "run.sh"
            script.write_text("#!/bin/sh\nexit 0\n")
            script.chmod(0o755)
    (source / "agents").mkdir()
    (source / "agents/poteto-agent.md").write_text("A delegate profile.\n")
    (source / "docs").mkdir()
    (source / "docs/guide.md").write_text("Guide.\n")
    (source / "LICENSE").write_text("MIT\n")
    (source / "README.md").write_text("[Excluded](skills/make-bot-ui/SKILL.md)\n")
    (source / "plugin.json").write_text('{"name":"pstack","version":"1.2.3"}')
    (project / "adapters").mkdir()
    (project / "adapters/common.md").write_text("Harness @HARNESS@\n")
    for target in ("codex", "antigravity"):
        (project / f"adapters/{target}.md").write_text(target + "\n")
    (project / "adapters/setup-pstack.md").write_text("# Setup @HARNESS@\n@ROLES@\n")
    (project / "src").mkdir()
    (project / "src/build.py").write_text("# fixture adapter source\n")
    lock = {"commit": "a" * 40, "version": "1.2.3", "files": inventory(source)}
    (project / "upstream.lock").write_bytes(canonical(lock))
    review(project, accept=True)
    return source


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name)
        self.source = fixture(self.project)

    def tearDown(self):
        self.tmp.cleanup()

    def test_reproducible_bundles_and_archives(self):
        first = self.project / "first"
        second = self.project / "second"
        build(self.project, first)
        build(self.project, second)
        self.assertEqual(inventory(first), inventory(second))
        a = package(first, self.project / "a.tar.gz")
        b = package(second, self.project / "b.tar.gz")
        self.assertEqual(a["sha256"], b["sha256"])

    def test_preserves_upstream_and_generates_metadata_dependencies(self):
        before = inventory(self.source)
        result = build(self.project)
        self.assertEqual(before, inventory(self.source))
        output = Path(result["output"])
        m = json.loads((output / "bundle.json").read_text())
        for target, variant in m["variants"].items():
            root = output / variant["root"]
            self.assertFalse((root / "skills/make-bot-ui").exists())
            self.assertFalse((root / "agents").exists())
            self.assertTrue((root / "agent-profiles/poteto-agent.md").exists())
            alpha = next(c for c in variant["components"] if c["id"] == "skill:alpha")
            self.assertIn("skill:beta", alpha["requires"])
            self.assertTrue(os.access(root / "skills/alpha/run.sh", os.X_OK))
            self.assertIn("a" * 40, (root / "README.md").read_text())
            setup = (root / "skills/setup-pstack/SKILL.md").read_text()
            self.assertIn("worker", setup)
            self.assertNotIn("cursor-model", setup)
        metadata = output / "bundles/codex/skills/alpha/agents/openai.yaml"
        self.assertIn("allow_implicit_invocation: false", metadata.read_text())
        self.assertNotIn("disable-model-invocation:", (output / "bundles/codex/skills/alpha/SKILL.md").read_text())

    def test_broken_skill_links_fail_the_build(self):
        path = self.source / "skills/alpha/SKILL.md"
        path.write_text(path.read_text() + "[missing](references/missing.md)\n")
        lock = json.loads((self.project / "upstream.lock").read_text())
        lock["files"] = inventory(self.source)
        (self.project / "upstream.lock").write_bytes(canonical(lock))
        review(self.project, accept=True)
        with self.assertRaisesRegex(Error, "Unresolved skill reference"):
            build(self.project)

    def test_changed_source_requires_sync_then_review(self):
        p = self.source / "skills/alpha/SKILL.md"
        p.write_text(p.read_text() + "new behavior\n")
        with self.assertRaisesRegex(Error, "upstream.lock"):
            build(self.project)
        lock = json.loads((self.project / "upstream.lock").read_text())
        lock["files"] = inventory(self.source)
        (self.project / "upstream.lock").write_bytes(canonical(lock))
        with self.assertRaisesRegex(Error, "unreviewed"):
            build(self.project)
        candidate = build(self.project, candidate=True)
        self.assertEqual(candidate["status"], "candidate")
        self.assertIn("skills/alpha/SKILL.md", review(self.project)["modified"])
        review(self.project, accept=True)
        self.assertEqual(build(self.project)["status"], "reviewed")

    def test_adapter_change_changes_release_identity(self):
        a = build(self.project)
        guide = self.project / "adapters/codex.md"
        guide.write_text(guide.read_text() + "Updated adapter.\n")
        b = build(self.project)
        self.assertNotEqual(a["version"], b["version"])

    def test_changed_setup_shape_fails_closed(self):
        p = self.source / "skills/setup-pstack/SKILL.md"
        p.write_text(p.read_text().replace("# budget:", "# new format:"))
        lock = json.loads((self.project / "upstream.lock").read_text())
        lock["files"] = inventory(self.source)
        (self.project / "upstream.lock").write_bytes(canonical(lock))
        review(self.project, accept=True)
        with self.assertRaisesRegex(Error, "role block changed"):
            build(self.project)


if __name__ == "__main__":
    unittest.main()
