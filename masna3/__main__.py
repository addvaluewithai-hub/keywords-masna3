"""Command line entry point: python -m masna3."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .engine import config_for, run_project
from .agent_jobs import process_jobs


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(
        description="Keywords Masna3: free-first keyword discovery with provenance"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="Research one project")
    run.add_argument("--project", required=True)
    run.add_argument("--providers", default="brave",
                     help="Comma-separated: brave,google,duckduckgo, or none")
    run.add_argument("--allow-unofficial", action="store_true",
                     help="Explicitly opt in to non-official suggestion endpoints")
    run.add_argument("--per-locale", type=int, default=4)
    run.add_argument("--refresh-days", type=int, default=21)
    listing = sub.add_parser("projects", help="List configured projects")
    sub.add_parser("process-jobs", help="Internal GitHub Actions agent worker")
    sub.add_parser("plan-all", help="Internal agent planner for all projects")
    args = parser.parse_args()
    if args.command == "projects":
        for path in sorted((root / "projects").glob("*/project.json")):
            print(path.parent.name)
        return 0
    if args.command == "process-jobs":
        print(json.dumps(process_jobs(root), ensure_ascii=False, indent=2))
        return 0
    if args.command == "plan-all":
        from .brain import plan_all
        print(json.dumps(plan_all(root), ensure_ascii=False, indent=2))
        return 0
    try:
        config_for(root, args.project)
        providers = [] if args.providers.strip().lower() == "none" else [
            p.strip().lower() for p in args.providers.split(",") if p.strip()
        ]
        result = run_project(
            root, args.project, providers, per_locale=args.per_locale,
            allow_unofficial=args.allow_unofficial,
            refresh_days=args.refresh_days,
        )
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
