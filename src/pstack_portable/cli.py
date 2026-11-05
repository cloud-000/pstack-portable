import argparse
import json
import subprocess
import sys
from pathlib import Path

from .build import Error, build, package, review, sync


def main(argv=None):
    p = argparse.ArgumentParser(description="Sync upstream pstack and compile reviewed harness bundles")
    p.add_argument("--project", type=Path, default=Path.cwd())
    commands = p.add_subparsers(dest="command", required=True)
    s = commands.add_parser("sync")
    s.add_argument("--ref", default="main")
    s.add_argument("--offline", action="store_true")
    s = commands.add_parser("review")
    s.add_argument("--accept", action="store_true", help="Record the current inputs after reviewing their diff and adaptation coverage")
    s = commands.add_parser("build")
    s.add_argument("--output", type=Path)
    s.add_argument("--candidate", action="store_true", help="Generate inspectable unreviewed output; not an installable release")
    s = commands.add_parser("package")
    s.add_argument("--bundle", type=Path)
    s.add_argument("--output", type=Path)
    args = p.parse_args(argv)
    try:
        if args.command == "sync":
            result = sync(args.project, args.ref, args.offline)
        elif args.command == "review":
            result = review(args.project, args.accept)
        elif args.command == "build":
            result = build(args.project, args.output, args.candidate)
        else:
            result = package(args.bundle or args.project / "dist/bundle", args.output or args.project / "dist/pstack-portable.tar.gz")
        print(json.dumps(result, indent=2))
        return 0
    except (Error, OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print(f"pstack-portable: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
