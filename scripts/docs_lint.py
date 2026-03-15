#!/usr/bin/env python3
"""Lint docs structure, frontmatter, links, and freshness."""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_ROOT = REPO_ROOT / "docs"

REQUIRED_DIRS = [
    DOCS_ROOT / "design-docs",
    DOCS_ROOT / "product-specs",
    DOCS_ROOT / "runbooks",
    DOCS_ROOT / "exec-plans" / "active",
    DOCS_ROOT / "exec-plans" / "completed",
    DOCS_ROOT / "references",
    DOCS_ROOT / "generated",
]

REQUIRED_FILES = [
    REPO_ROOT / "AGENTS.md",
    REPO_ROOT / "ARCHITECTURE.md",
    DOCS_ROOT / "index.md",
    DOCS_ROOT / "PLANS.md",
    DOCS_ROOT / "SECURITY.md",
    DOCS_ROOT / "RELIABILITY.md",
    DOCS_ROOT / "CLIENTS.md",
    DOCS_ROOT / "design-docs" / "index.md",
    DOCS_ROOT / "design-docs" / "core-beliefs.md",
    DOCS_ROOT / "product-specs" / "index.md",
    DOCS_ROOT / "exec-plans" / "tech-debt-tracker.md",
]

REQUIRED_FRONTMATTER_KEYS = {
    "owner",
    "status",
    "last_verified",
    "source_of_truth",
    "related_code",
    "related_tests",
    "review_cycle_days",
}

FRONTMATTER_DOC_STATUSES = {"draft", "verified", "deprecated", "generated", "active"}
LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def _extract_frontmatter(text: str) -> str | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    return text[4:end]


def _parse_frontmatter(meta: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    current_key: str | None = None
    for raw_line in meta.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        if re.match(r"^[A-Za-z0-9_]+:", line):
            key, value = line.split(":", 1)
            parsed[key.strip()] = value.strip()
            current_key = key.strip()
            continue
        if current_key and line.lstrip().startswith("- "):
            parsed[current_key] = (parsed.get(current_key, "") + " " + line.lstrip()[2:]).strip()
    return parsed


def _doc_files() -> list[Path]:
    files = [p for p in DOCS_ROOT.rglob("*") if p.is_file() and p.suffix.lower() in {".md", ".txt"}]
    files.extend([REPO_ROOT / "AGENTS.md", REPO_ROOT / "ARCHITECTURE.md"])
    seen: set[Path] = set()
    unique: list[Path] = []
    for file in files:
        resolved = file.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(file)
    return sorted(unique)


def _check_link_target(source_file: Path, target: str) -> str | None:
    target = target.strip()
    if not target or target.startswith(("http://", "https://", "mailto:", "#")):
        return None
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1].strip()
    if target.startswith("/"):
        path = REPO_ROOT / target.lstrip("/")
    else:
        path = (source_file.parent / target).resolve()
    if not path.exists():
        return f"{source_file.relative_to(REPO_ROOT)} -> missing link target: {target}"
    return None


def lint(enforce_stale: bool) -> int:
    errors: list[str] = []
    warnings: list[str] = []
    today = dt.date.today()

    for required_dir in REQUIRED_DIRS:
        if not required_dir.exists():
            errors.append(f"Missing required directory: {required_dir.relative_to(REPO_ROOT)}")

    for required_file in REQUIRED_FILES:
        if not required_file.exists():
            errors.append(f"Missing required file: {required_file.relative_to(REPO_ROOT)}")

    for file in _doc_files():
        text = file.read_text(encoding="utf-8")
        if file.suffix.lower() == ".txt":
            continue
        frontmatter = _extract_frontmatter(text)
        if frontmatter is None:
            errors.append(f"{file.relative_to(REPO_ROOT)} missing frontmatter block")
            continue
        parsed = _parse_frontmatter(frontmatter)
        missing = REQUIRED_FRONTMATTER_KEYS - set(parsed)
        if missing:
            errors.append(f"{file.relative_to(REPO_ROOT)} missing frontmatter keys: {sorted(missing)}")
            continue

        status = parsed["status"]
        if status not in FRONTMATTER_DOC_STATUSES:
            errors.append(
                f"{file.relative_to(REPO_ROOT)} has invalid status '{status}', "
                f"expected one of {sorted(FRONTMATTER_DOC_STATUSES)}"
            )

        try:
            last_verified = dt.date.fromisoformat(parsed["last_verified"])
        except ValueError:
            errors.append(f"{file.relative_to(REPO_ROOT)} has invalid last_verified date")
            last_verified = today

        try:
            cycle_days = int(parsed["review_cycle_days"])
        except ValueError:
            errors.append(f"{file.relative_to(REPO_ROOT)} has invalid review_cycle_days value")
            cycle_days = 0

        if status not in {"deprecated", "generated"} and cycle_days > 0:
            age = (today - last_verified).days
            if age > cycle_days:
                msg = (
                    f"{file.relative_to(REPO_ROOT)} stale by {age - cycle_days} days "
                    f"(age={age}, review_cycle_days={cycle_days})"
                )
                if enforce_stale:
                    errors.append(msg)
                else:
                    warnings.append(msg)

        for link in LINK_PATTERN.findall(text):
            maybe_error = _check_link_target(file, link)
            if maybe_error:
                errors.append(maybe_error)

    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")

    if errors:
        print(f"docs_lint failed with {len(errors)} error(s)")
        return 1
    print("docs_lint passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint docs structure and metadata.")
    parser.add_argument(
        "--enforce-stale",
        action="store_true",
        help="Treat stale documents as errors.",
    )
    args = parser.parse_args()
    return lint(enforce_stale=args.enforce_stale)


if __name__ == "__main__":
    sys.exit(main())
