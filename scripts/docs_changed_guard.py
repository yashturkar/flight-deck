#!/usr/bin/env python3
"""Fail PRs when code changes do not include docs context updates."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOC_PATHS = {"AGENTS.md", "ARCHITECTURE.md"}
CODE_PREFIXES = ("kb-server/", "vault-sync/")
NON_CODE_PREFIXES = ("docs/", ".github/", "scripts/")


def _git_diff_names(base: str, head: str) -> list[str]:
    cmd = ["git", "diff", "--name-only", base, head]
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "git diff failed")
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _is_code_file(path: str) -> bool:
    if not path.startswith(CODE_PREFIXES):
        return False
    if path.startswith(NON_CODE_PREFIXES):
        return False
    return path.endswith(".py") or "/tests/" in path or path.endswith((".md", ".service", ".toml", ".sh"))


def _is_context_doc(path: str) -> bool:
    if path in DOC_PATHS:
        return True
    return path.startswith("docs/")


def main() -> int:
    parser = argparse.ArgumentParser(description="Require docs updates for code changes.")
    parser.add_argument("--base", required=True, help="Base git ref")
    parser.add_argument("--head", required=True, help="Head git ref")
    args = parser.parse_args()

    try:
        changed = _git_diff_names(args.base, args.head)
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        return 2

    if not changed:
        print("No changed files detected.")
        return 0

    code_changes = [p for p in changed if _is_code_file(p) and not _is_context_doc(p)]
    doc_changes = [p for p in changed if _is_context_doc(p)]

    if not code_changes:
        print("No code-impacting files changed; docs guard passes.")
        return 0

    if doc_changes:
        print("Docs guard passes: code changes include context doc updates.")
        return 0

    print("ERROR: code-impacting changes detected without docs updates.")
    print("Changed code files:")
    for path in code_changes:
        print(f" - {path}")
    print("Required: update at least one of docs/*, AGENTS.md, or ARCHITECTURE.md")
    return 1


if __name__ == "__main__":
    sys.exit(main())

