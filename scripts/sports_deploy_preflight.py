#!/usr/bin/env python3
"""Read-only preflight for a manual Sports HULK deployment.

This script NEVER fetches, resets, pulls, copies, deletes, or restarts.
Run git fetch origin main separately when refreshing remote tracking data.
A production change still requires a separately approved, backed-up deployment
on the authorized VPS.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=check,
    )


def paths(root: Path, *args: str) -> set[str]:
    result = subprocess.run(
        ["git", "-C", str(root), *args, "-z"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return {v.decode("utf-8", errors="replace") for v in result.stdout.split(b"\0") if v}


def inspect(root: Path, target: str) -> dict:
    result = {
        "status": "BLOCKED",
        "live_root": str(root.resolve()),
        "target_ref": target,
        "live_head": None,
        "target_sha": None,
        "incoming_changes": 0,
        "preserved_local_changes": 0,
        "reasons": [],
    }
    problems: list[str] = result["reasons"]

    if not root.is_dir():
        problems.append("Live repository directory is missing.")
        return result
    toplevel = git(root, "rev-parse", "--show-toplevel", check=False)
    if toplevel.returncode or Path(toplevel.stdout.strip()).resolve() != root.resolve():
        problems.append("Target directory is not a Git repository root.")
        return result

    branch = git(root, "symbolic-ref", "--short", "HEAD", check=False)
    if branch.returncode or branch.stdout.strip() != "main":
        problems.append("Live repository must be on main.")

    current = git(root, "rev-parse", "--verify", "HEAD", check=False)
    incoming = git(root, "rev-parse", "--verify", f"{target}^{{commit}}", check=False)
    if current.returncode or incoming.returncode:
        problems.append("Cannot resolve local HEAD and target. Fetch main first.")
        return result
    live_head, target_sha = current.stdout.strip(), incoming.stdout.strip()
    result["live_head"], result["target_sha"] = live_head, target_sha

    ancestry = git(root, "merge-base", "--is-ancestor", live_head, target_sha, check=False)
    if ancestry.returncode:
        problems.append("Target is behind or divergent from live: never reset live history.")
        return result

    incoming_paths = paths(root, "diff", "--name-only", live_head, target_sha)
    removed_paths = paths(root, "diff", "--name-only", "--diff-filter=D", live_head, target_sha)
    changed_tracked = paths(root, "diff", "--name-only") | paths(root, "diff", "--cached", "--name-only")
    untracked = paths(root, "ls-files", "--others", "--exclude-standard")

    result["incoming_changes"] = len(incoming_paths)
    result["preserved_local_changes"] = len(changed_tracked | untracked)
    if removed_paths:
        problems.append(f"Incoming release deletes {len(removed_paths)} tracked paths; requires separate review.")
    collisions = incoming_paths & (changed_tracked | untracked)
    if collisions:
        problems.append("Incoming release conflicts with local edits: " + ", ".join(sorted(collisions)[:5]))

    local_frontend = {
        name for name in changed_tracked | untracked
        if name.startswith("commercial_web/")
        and not name.startswith("commercial_web/dist/")
    }
    if local_frontend:
        problems.append(
            "Uncommitted commercial frontend changes must be reconciled before publishing: "
            + ", ".join(sorted(local_frontend)[:5])
        )

    if live_head == target_sha:
        result["status"] = "ALREADY_AT_TARGET" if not problems else "BLOCKED"
    elif not problems:
        result["status"] = "PREFLIGHT_PASS"

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path("/home/ubuntu/sports-hulk"),
        help="The live repo root; defaults to the Sports HULK VPS path",
    )
    parser.add_argument("--target", default="origin/main", help="Existing local Git commit/ref, normally origin/main")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        report = inspect(args.root, args.target)
    except (OSError, subprocess.CalledProcessError) as exc:
        report = {"status": "BLOCKED", "reasons": [str(exc)]}
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"DEPLOY PREFLIGHT: {report['status']}")
        print(f"Live: {report.get('live_head') or 'unknown'} / Target: {report.get('target_sha') or 'unknown'}")
        print(f"Changed incoming files: {report.get('incoming_changes', 0)}")
        for reason in report.get("reasons", []):
            print(f"BLOCKED: {reason}")
        print("Read-only: no live files, Git refs, or services changed.")
    return 0 if report["status"] in {"PREFLIGHT_PASS", "ALREADY_AT_TARGET"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
