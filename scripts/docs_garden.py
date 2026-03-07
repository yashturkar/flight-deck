#!/usr/bin/env python3
"""Generate stale-doc and ownership reports for maintenance."""

from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_ROOT = REPO_ROOT / "docs"


def _extract_frontmatter(text: str) -> str | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    return text[4:end]


def _parse_frontmatter(meta: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in meta.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def _docs() -> list[Path]:
    files = [p for p in DOCS_ROOT.rglob("*.md")]
    files.extend([REPO_ROOT / "AGENTS.md", REPO_ROOT / "ARCHITECTURE.md"])
    return sorted(set(files))


def _update_last_verified(path: Path, today: dt.date) -> bool:
    text = path.read_text(encoding="utf-8")
    frontmatter = _extract_frontmatter(text)
    if frontmatter is None:
        return False
    updated_frontmatter, count = re.subn(
        r"(?m)^last_verified:\s*\d{4}-\d{2}-\d{2}\s*$",
        f"last_verified: {today.isoformat()}",
        frontmatter,
        count=1,
    )
    if count == 0 or updated_frontmatter == frontmatter:
        return False
    new_text = text.replace(frontmatter, updated_frontmatter, 1)
    path.write_text(new_text, encoding="utf-8")
    return True


def build_report() -> str:
    today = dt.date.today()
    stale: list[tuple[str, str, int]] = []
    missing_meta: list[str] = []
    by_owner: dict[str, int] = {}

    for path in _docs():
        text = path.read_text(encoding="utf-8")
        frontmatter = _extract_frontmatter(text)
        rel = str(path.relative_to(REPO_ROOT))
        if not frontmatter:
            missing_meta.append(rel)
            continue
        meta = _parse_frontmatter(frontmatter)
        owner = meta.get("owner", "unknown")
        by_owner[owner] = by_owner.get(owner, 0) + 1

        status = meta.get("status", "draft")
        if status in {"deprecated", "generated"}:
            continue

        try:
            verified = dt.date.fromisoformat(meta.get("last_verified", ""))
            cycle = int(meta.get("review_cycle_days", "0"))
        except ValueError:
            missing_meta.append(rel)
            continue
        age = (today - verified).days
        if cycle > 0 and age > cycle:
            stale.append((rel, owner, age - cycle))

    lines = [
        "---",
        "owner: platform",
        "status: generated",
        f"last_verified: {today.isoformat()}",
        "source_of_truth:",
        "  - ../../scripts/docs_garden.py",
        "related_code:",
        "  - ../../scripts/docs_lint.py",
        "related_tests:",
        "  - ../../kb-server/tests",
        "  - ../../vault-sync/tests",
        "review_cycle_days: 7",
        "---",
        "",
        "# Stale Documentation Report",
        "",
        f"Generated: `{today.isoformat()}`",
        "",
        "## Ownership Summary",
        "",
        "| Owner | Document Count |",
        "| --- | --- |",
    ]
    for owner, count in sorted(by_owner.items()):
        lines.append(f"| `{owner}` | {count} |")

    lines.extend(["", "## Stale Docs", "", "| File | Owner | Days Over SLA |", "| --- | --- | --- |"])
    if stale:
        for file, owner, days in stale:
            lines.append(f"| `{file}` | `{owner}` | {days} |")
    else:
        lines.append("| _none_ | - | - |")

    lines.extend(["", "## Missing or Invalid Metadata", ""])
    if missing_meta:
        for file in sorted(set(missing_meta)):
            lines.append(f"- `{file}`")
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Suggested Actions",
            "",
            "- refresh stale docs and update `last_verified`",
            "- correct frontmatter schema mismatches",
            "- convert repeated stale docs into tracked debt items",
        ]
    )
    return "\n".join(lines) + "\n"


def autofix_stale_last_verified(today: dt.date) -> int:
    fixed = 0
    for path in _docs():
        text = path.read_text(encoding="utf-8")
        frontmatter = _extract_frontmatter(text)
        if not frontmatter:
            continue
        meta = _parse_frontmatter(frontmatter)
        status = meta.get("status", "draft")
        if status in {"deprecated", "generated"}:
            continue
        try:
            verified = dt.date.fromisoformat(meta.get("last_verified", ""))
            cycle = int(meta.get("review_cycle_days", "0"))
        except ValueError:
            continue
        age = (today - verified).days
        if cycle > 0 and age > cycle and _update_last_verified(path, today):
            fixed += 1
    return fixed


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate stale documentation report.")
    parser.add_argument(
        "--output",
        default="docs/generated/stale-docs-report.md",
        help="Output path relative to repository root.",
    )
    parser.add_argument(
        "--autofix-last-verified",
        action="store_true",
        help="Update last_verified to today for stale docs before generating the report.",
    )
    args = parser.parse_args()

    today = dt.date.today()
    if args.autofix_last_verified:
        fixed = autofix_stale_last_verified(today)
        print(f"Auto-fixed stale last_verified for {fixed} document(s)")

    out_path = (REPO_ROOT / args.output).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(build_report(), encoding="utf-8")
    print(f"Wrote {out_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
