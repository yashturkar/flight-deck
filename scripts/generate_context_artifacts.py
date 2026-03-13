#!/usr/bin/env python3
"""Generate docs artifacts from code/config sources."""

from __future__ import annotations

import datetime as dt
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_GENERATED = REPO_ROOT / "docs" / "generated"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _git_last_change_date(paths: list[Path]) -> str:
    dates: list[str] = []
    for path in paths:
        proc = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", str(path)],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        value = proc.stdout.strip()
        if value:
            dates.append(value)
    if dates:
        return max(dates)
    return "1970-01-01"


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


def _write_api_surface() -> None:
    health_path = REPO_ROOT / "kb-server" / "app" / "api" / "routes" / "health.py"
    context_path = REPO_ROOT / "kb-server" / "app" / "api" / "routes" / "context.py"
    notes_path = REPO_ROOT / "kb-server" / "app" / "api" / "routes" / "notes.py"
    publish_path = REPO_ROOT / "kb-server" / "app" / "api" / "routes" / "publish.py"
    health_routes = _parse_routes(health_path)
    context_routes = _parse_routes(context_path)
    notes_routes = _parse_routes(notes_path)
    publish_routes = _parse_routes(publish_path)
    all_routes = health_routes + context_routes + notes_routes + publish_routes
    date = _git_last_change_date([health_path, context_path, notes_path, publish_path])

    content = [
        "---",
        "owner: platform",
        "status: generated",
        f"last_verified: {date}",
        "source_of_truth:",
        "  - ../../kb-server/app/api/routes/health.py",
        "  - ../../kb-server/app/api/routes/context.py",
        "  - ../../kb-server/app/api/routes/notes.py",
        "  - ../../kb-server/app/api/routes/publish.py",
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
    (DOCS_GENERATED / "api-surface.md").write_text("\n".join(content) + "\n", encoding="utf-8")


def _write_env_catalog() -> None:
    kb_env_path = REPO_ROOT / "kb-server" / ".env.example"
    kb_config_path = REPO_ROOT / "kb-server" / "app" / "core" / "config.py"
    mcp_config_path = REPO_ROOT / "mcp-server" / "mcp_server" / "config.py"
    vs_config_path = REPO_ROOT / "vault-sync" / "vault_sync" / "config.py"
    date = _git_last_change_date([kb_env_path, kb_config_path, mcp_config_path, vs_config_path])
    kb_env = _parse_env_example(kb_env_path)
    kb_defaults = _parse_settings_defaults(kb_config_path)
    mcp_defaults = _parse_settings_defaults(mcp_config_path, class_name="MCPServerSettings")
    vs_defaults = _parse_settings_defaults(vs_config_path)

    content = [
        "---",
        "owner: platform",
        "status: generated",
        f"last_verified: {date}",
        "source_of_truth:",
        "  - ../../kb-server/.env.example",
        "  - ../../kb-server/app/core/config.py",
        "  - ../../mcp-server/mcp_server/config.py",
        "  - ../../vault-sync/vault_sync/config.py",
        "related_code:",
        "  - ../../scripts/generate_context_artifacts.py",
        "related_tests:",
        "  - ../../kb-server/tests",
        "  - ../../mcp-server/tests",
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
            "## mcp-server Settings Defaults",
            "",
            "| Field | Default Expression |",
            "| --- | --- |",
        ]
    )
    for key, value in mcp_defaults:
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
    (DOCS_GENERATED / "env-catalog.md").write_text("\n".join(content) + "\n", encoding="utf-8")


def main() -> int:
    DOCS_GENERATED.mkdir(parents=True, exist_ok=True)
    _write_api_surface()
    _write_env_catalog()
    print("Generated docs/generated/api-surface.md and docs/generated/env-catalog.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
