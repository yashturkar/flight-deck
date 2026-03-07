"""GitHub API client for PR management."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


class GitHubError(Exception):
    pass


def _headers() -> dict[str, str]:
    if not settings.github_token:
        raise GitHubError(
            "GITHUB_TOKEN not configured. Set it in .env to enable PR creation."
        )
    return {
        "Authorization": f"Bearer {settings.github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _repo_path() -> str:
    if not settings.github_repo:
        raise GitHubError(
            "GITHUB_REPO not configured. Set it in .env (e.g., 'owner/repo')."
        )
    return settings.github_repo


def find_open_pr(head_branch: str, base_branch: str | None = None) -> dict[str, Any] | None:
    """Find an existing open PR for the given head branch."""
    base = base_branch or settings.git_branch
    repo = _repo_path()

    url = f"{GITHUB_API}/repos/{repo}/pulls"
    params = {"head": head_branch, "base": base, "state": "open"}

    with httpx.Client(timeout=30) as client:
        resp = client.get(url, headers=_headers(), params=params)

    if resp.status_code != 200:
        log.warning("GitHub API error listing PRs: %s %s", resp.status_code, resp.text)
        return None

    prs = resp.json()

    owner = repo.split("/")[0]
    full_head = f"{owner}:{head_branch}"

    for pr in prs:
        if pr.get("head", {}).get("label") == full_head:
            return pr

    return None


def create_pr(
    head_branch: str,
    title: str,
    body: str = "",
    base_branch: str | None = None,
) -> dict[str, Any]:
    """Create a new pull request."""
    base = base_branch or settings.git_branch
    repo = _repo_path()

    url = f"{GITHUB_API}/repos/{repo}/pulls"
    payload = {
        "title": title,
        "head": head_branch,
        "base": base,
        "body": body,
    }

    with httpx.Client(timeout=30) as client:
        resp = client.post(url, headers=_headers(), json=payload)

    if resp.status_code not in (200, 201):
        raise GitHubError(
            f"Failed to create PR: {resp.status_code} {resp.text}"
        )

    pr = resp.json()
    log.info("Created PR #%s: %s", pr["number"], pr["html_url"])
    return pr


def update_pr(
    pr_number: int,
    title: str | None = None,
    body: str | None = None,
) -> dict[str, Any]:
    """Update an existing pull request."""
    repo = _repo_path()
    url = f"{GITHUB_API}/repos/{repo}/pulls/{pr_number}"

    payload: dict[str, str] = {}
    if title:
        payload["title"] = title
    if body is not None:
        payload["body"] = body

    if not payload:
        raise GitHubError("Nothing to update")

    with httpx.Client(timeout=30) as client:
        resp = client.patch(url, headers=_headers(), json=payload)

    if resp.status_code != 200:
        raise GitHubError(
            f"Failed to update PR #{pr_number}: {resp.status_code} {resp.text}"
        )

    pr = resp.json()
    log.info("Updated PR #%s: %s", pr["number"], pr["html_url"])
    return pr


def list_open_prs(base_branch: str | None = None) -> list[dict[str, Any]]:
    """Return all open PRs targeting *base_branch* (default: main).

    Each dict contains at least ``number``, ``html_url``, and
    ``head.ref`` (the source branch name).
    """
    base = base_branch or settings.git_branch
    repo = _repo_path()
    url = f"{GITHUB_API}/repos/{repo}/pulls"
    params: dict[str, str] = {"base": base, "state": "open", "per_page": "100"}

    with httpx.Client(timeout=30) as client:
        resp = client.get(url, headers=_headers(), params=params)

    if resp.status_code != 200:
        log.warning("GitHub API error listing PRs: %s %s", resp.status_code, resp.text)
        return []

    return resp.json()


def list_open_kb_api_prs(base_branch: str | None = None) -> list[dict[str, Any]]:
    """Return open PRs whose head branch starts with the configured prefix.

    Typically these are ``kb-api/YYYY-MM-DD`` branches.
    """
    prefix = settings.git_batch_branch_prefix
    return [
        pr
        for pr in list_open_prs(base_branch)
        if pr.get("head", {}).get("ref", "").startswith(prefix)
    ]


def ensure_pr(
    head_branch: str,
    title: str,
    body: str = "",
    base_branch: str | None = None,
) -> dict[str, Any]:
    """Create a PR if none exists, otherwise return the existing one.

    Returns the PR dict with 'number', 'html_url', etc.
    """
    existing = find_open_pr(head_branch, base_branch)
    if existing:
        log.info("Found existing PR #%s for branch %s", existing["number"], head_branch)
        return existing

    return create_pr(head_branch, title, body, base_branch)
