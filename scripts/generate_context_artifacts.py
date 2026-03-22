#!/usr/bin/env python3
"""Generate docs artifacts from code/config sources."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_GENERATED = REPO_ROOT / "docs" / "generated"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _parse_env_example(path: Path) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    for line in _read(path).splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        items.append((key.strip(), value.strip()))
    return items


def _parse_settings_defaults(path: Path, class_name: str = "Settings") -> list[tuple[str, str]]:
    defaults: list[tuple[str, str]] = []
    in_class = False
    assignment_pattern = re.compile(r"^\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*:[^=]+=\s*(.+)\s*$")
    for line in _read(path).splitlines():
        if line.startswith(f"class {class_name}"):
            in_class = True
            continue
        if in_class and line and not line.startswith((" ", "\t")):
            break
        if in_class:
            match = assignment_pattern.match(line)
            if match:
                defaults.append((match.group(1), match.group(2)))
    return defaults


def _parse_routes(path: Path) -> list[tuple[str, str]]:
    routes: list[tuple[str, str]] = []
    pattern = re.compile(r'@router\.(get|put|post|delete|patch)\("([^"]+)"')
    for line in _read(path).splitlines():
        match = pattern.search(line)
        if match:
            routes.append((match.group(1).upper(), match.group(2)))
    return routes


def _last_commit_date(paths: list[Path]) -> str:
    rel_paths = [str(path.relative_to(REPO_ROOT)) for path in paths]
    result = subprocess.run(
        ["git", "log", "-1", "--format=%cs", "--", *rel_paths],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _write_api_surface() -> None:
    route_paths = [
        REPO_ROOT / "kb-server" / "app" / "api" / "routes" / "health.py",
        REPO_ROOT / "kb-server" / "app" / "api" / "routes" / "notes.py",
        REPO_ROOT / "kb-server" / "app" / "api" / "routes" / "publish.py",
        REPO_ROOT / "kb-server" / "app" / "api" / "routes" / "admin.py",
    ]
    all_routes: list[tuple[str, str]] = []
    for route_path in route_paths:
        all_routes.extend(_parse_routes(route_path))
    date = _last_commit_date(route_paths)

    content = [
        "---",
        "owner: platform",
        "status: generated",
        f"last_verified: {date}",
        "source_of_truth:",
        "  - ../../kb-server/app/api/routes/health.py",
        "  - ../../kb-server/app/api/routes/notes.py",
        "  - ../../kb-server/app/api/routes/publish.py",
        "  - ../../kb-server/app/api/routes/admin.py",
        "related_code:",
        "  - ../../scripts/generate_context_artifacts.py",
        "related_tests:",
        "  - ../../kb-server/tests",
        "review_cycle_days: 7",
        "---",
        "",
        "# API Surface (Generated)",
        "",
        f"Generated on `{date}` from route handlers.",
        "",
        "| Method | Path |",
        "| --- | --- |",
    ]
    for method, path in all_routes:
        content.append(f"| `{method}` | `{path}` |")
    content.append("")
    content.append("Do not edit manually. Regenerate with `python3 scripts/generate_context_artifacts.py`.")
    (DOCS_GENERATED / "api-surface.md").write_text("\n".join(content), encoding="utf-8")


def _write_env_catalog() -> None:
    kb_env_path = REPO_ROOT / "kb-server" / ".env.example"
    kb_settings_path = REPO_ROOT / "kb-server" / "app" / "core" / "config.py"
    vs_settings_path = REPO_ROOT / "vault-sync" / "vault_sync" / "config.py"
    date = _last_commit_date([kb_env_path, kb_settings_path, vs_settings_path])
    kb_env = _parse_env_example(kb_env_path)
    kb_defaults = _parse_settings_defaults(kb_settings_path)
    vs_defaults = _parse_settings_defaults(vs_settings_path)

    content = [
        "---",
        "owner: platform",
        "status: generated",
        f"last_verified: {date}",
        "source_of_truth:",
        "  - ../../kb-server/.env.example",
        "  - ../../kb-server/app/core/config.py",
        "  - ../../vault-sync/vault_sync/config.py",
        "related_code:",
        "  - ../../scripts/generate_context_artifacts.py",
        "related_tests:",
        "  - ../../kb-server/tests",
        "  - ../../vault-sync/tests",
        "review_cycle_days: 7",
        "---",
        "",
        "# Environment Catalog (Generated)",
        "",
        f"Generated on `{date}` from settings and env sources.",
        "",
        "## kb-server `.env.example`",
        "",
        "| Variable | Example Default |",
        "| --- | --- |",
    ]
    for key, value in kb_env:
        redacted = "<redacted>" if "KEY" in key or "TOKEN" in key else value
        content.append(f"| `{key}` | `{redacted}` |")

    content.extend(
        [
            "",
            "## kb-server Settings Defaults",
            "",
            "| Field | Default Expression |",
            "| --- | --- |",
        ]
    )
    for key, value in kb_defaults:
        content.append(f"| `{key}` | `{value}` |")

    content.extend(
        [
            "",
            "## vault-sync Settings Defaults",
            "",
            "| Field | Default Expression |",
            "| --- | --- |",
        ]
    )
    for key, value in vs_defaults:
        content.append(f"| `{key}` | `{value}` |")

    content.append("")
    content.append("Do not edit manually. Regenerate with `python3 scripts/generate_context_artifacts.py`.")
    (DOCS_GENERATED / "env-catalog.md").write_text("\n".join(content), encoding="utf-8")


def main() -> int:
    DOCS_GENERATED.mkdir(parents=True, exist_ok=True)
    _write_api_surface()
    _write_env_catalog()
    print("Generated docs/generated/api-surface.md and docs/generated/env-catalog.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
