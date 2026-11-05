#!/usr/bin/env python3
"""Exercise the producer/manager contract through public CLIs in a temporary home."""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skillsctl", type=Path, required=True, help="Path to the independent skillsctl checkout")
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    producer = project / "bin/pstack-portable"
    manager = args.skillsctl.expanduser().resolve() / "bin/skillsctl"
    subprocess.run([sys.executable, str(producer), "build"], check=True, capture_output=True)
    source = project / "dist/bundle"
    with tempfile.TemporaryDirectory(prefix="pstack-integration-") as temporary:
        root = Path(temporary)
        home = root / "home"

        def run(*commands):
            result = subprocess.run([sys.executable, str(manager), "--home", str(home), *map(str, commands)], text=True, capture_output=True)
            if result.returncode:
                raise RuntimeError(result.stderr)
            return json.loads(result.stdout)

        run("validate", source)
        first = run("install", source, "--harness", "codex", "--harness", "antigravity")
        run("doctor")
        paths = {"codex": home / ".agents/skills", "antigravity": home / ".gemini/config/skills"}
        counts = {t: len(list(p.iterdir())) for t, p in paths.items()}
        assert counts["codex"] == counts["antigravity"] and counts["codex"] > 0
        run("disable", "pstack-portable", "--harness", "codex", "--skill", "sharpen", "--cascade")
        assert not (paths["codex"] / "sharpen").exists()
        assert (paths["antigravity"] / "sharpen").exists()
        run("rollback", "pstack-portable", "--harness", "codex", "--generation", first["generation"])
        run("disable", "pstack-portable", "--harness", "antigravity")
        assert not list(paths["antigravity"].iterdir())
        assert len(list(paths["codex"].iterdir())) == counts["codex"]
        run("enable", "pstack-portable", "--harness", "antigravity")

        newer = root / "newer-bundle"
        shutil.copytree(source, newer)
        manifest = json.loads((newer / "bundle.json").read_text())
        manifest["version"] += ".integration-test"
        for variant in manifest["variants"].values():
            relative = "skills/sharpen/SKILL.md"
            file = newer / variant["root"] / relative
            file.write_text(file.read_text() + "\nIntegration fixture revision.\n")
            variant["files"][relative]["sha256"] = hashlib.sha256(file.read_bytes()).hexdigest()
        (newer / "bundle.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
        run("update", "pstack-portable", "--source", newer, "--harness", "codex", "--harness", "antigravity")
        for path in paths.values():
            assert "Integration fixture revision" in (path / "sharpen/SKILL.md").read_text()
        # Remove the downloaded source to prove rollback uses the immutable store offline.
        shutil.rmtree(newer)
        run("rollback", "pstack-portable", "--harness", "codex", "--harness", "antigravity")
        for path in paths.values():
            assert "Integration fixture revision" not in (path / "sharpen/SKILL.md").read_text()
        run("doctor")
        print(json.dumps({"ok": True, "installedSkills": counts, "checks": ["validate", "install", "individual-disable", "package-disable-enable", "update", "offline-rollback", "doctor"]}, indent=2))


if __name__ == "__main__":
    main()
