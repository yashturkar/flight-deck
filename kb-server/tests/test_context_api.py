"""Tests for retrieval service and /context API routes."""

from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
import subprocess
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.db import Base, get_session
from app.services import retrieval_service

TEST_API_KEY = "test-secret-key-for-context"


def _git(vault: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=vault,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _commit_file(vault: Path, rel_path: str, content: str, msg: str) -> str:
    full = vault / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")
    _git(vault, "add", "--all")
    _git(vault, "commit", "-m", msg)
    return _git(vault, "rev-parse", "HEAD")


def _create_branch(vault: Path, branch: str) -> None:
    _git(vault, "checkout", "-b", branch)


def _checkout(vault: Path, branch: str) -> None:
    _git(vault, "checkout", branch)


@pytest.fixture(autouse=True)
def _patch_vault_settings(tmp_vault: Path):
    with patch("app.services.git_service.settings") as gs, \
         patch("app.services.vault_service.settings") as vs, \
         patch("app.services.current_view_service.settings") as cvs, \
         patch("app.services.retrieval_service.settings") as rs:
        for patched in (gs, vs, cvs, rs):
            patched.vault_path = tmp_vault
            patched.git_remote = "origin"
            patched.git_branch = "main"
            patched.git_batch_branch_prefix = "kb-api"
        yield


@pytest.fixture()
def vault_with_retrieval_graph(tmp_vault: Path) -> Path:
    _commit_file(
        tmp_vault,
        "notes/mcp-overview.md",
        """---
title: MCP Overview
tags: [mcp, agent]
---
# MCP Overview

Flight Deck exposes notes to agent clients.

See [[retrieval-layer]] for context bundling.
""",
        "add mcp overview",
    )
    _commit_file(
        tmp_vault,
        "notes/retrieval-layer.md",
        """---
tags:
  - retrieval
  - context
---
# Retrieval Layer

This note describes graph traversal and context bundles.
""",
        "add retrieval layer",
    )

    _create_branch(tmp_vault, "kb-api/2026-03-12")
    _commit_file(
        tmp_vault,
        "notes/mcp-adapter.md",
        """# MCP Adapter

The adapter uses the retrieval layer to return context bundles.
""",
        "add pending adapter",
    )
    _checkout(tmp_vault, "main")
    return tmp_vault


def _make_client(tmp_vault: Path) -> tuple[TestClient, ExitStack]:
    stack = ExitStack()
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    def _override_session():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    auth_settings = stack.enter_context(patch("app.api.deps.settings"))
    middleware_settings = stack.enter_context(patch("app.core.auth.settings"))
    auth_settings.kb_api_key = TEST_API_KEY
    middleware_settings.kb_api_key = TEST_API_KEY

    from app.main import create_app

    app = create_app()
    app.dependency_overrides[get_session] = _override_session
    client = TestClient(app)
    return client, stack


@pytest.fixture()
def client(tmp_vault: Path):
    client, stack = _make_client(tmp_vault)
    try:
        yield client
    finally:
        stack.close()


class TestRetrievalService:
    def test_graph_expansion_returns_related_note(self, vault_with_retrieval_graph: Path):
        results = retrieval_service.search_notes("mcp", view="main", limit=10)
        paths = [result.path for result in results]
        assert "notes/mcp-overview.md" in paths
        assert "notes/retrieval-layer.md" in paths

        retrieval_result = next(
            result for result in results if result.path == "notes/retrieval-layer.md"
        )
        assert any("linked from" in reason for reason in retrieval_result.reasons)

    def test_current_view_includes_pending_branch_content(self, vault_with_retrieval_graph: Path):
        with patch(
            "app.services.current_view_service.github_service.list_open_kb_api_prs",
            side_effect=Exception("offline"),
        ):
            results = retrieval_service.search_notes("adapter", view="current", limit=10)

        adapter_result = next(
            result for result in results if result.path == "notes/mcp-adapter.md"
        )
        assert "kb-api/2026-03-12" in adapter_result.sources

    def test_bundle_respects_token_budget(self, tmp_vault: Path):
        _commit_file(
            tmp_vault,
            "notes/short.md",
            "# Retrieval Short\n\nretrieval token\n",
            "add short",
        )
        _commit_file(
            tmp_vault,
            "notes/long.md",
            "# Retrieval Long\n\n" + "retrieval " * 300,
            "add long",
        )

        items, used_tokens = retrieval_service.build_context_bundle(
            "retrieval",
            view="main",
            limit=10,
            token_budget=20,
        )

        assert used_tokens <= 20
        assert any(item.content is not None for item in items)
        assert any(item.truncated for item in items)


class TestContextAPI:
    headers = {"X-API-Key": TEST_API_KEY}

    def test_search_requires_api_key(self, client: TestClient):
        response = client.post("/context/search", json={"query": "mcp"})
        assert response.status_code == 401

    def test_search_returns_current_view_results(self, client: TestClient, vault_with_retrieval_graph: Path):
        with patch(
            "app.services.current_view_service.github_service.list_open_kb_api_prs",
            side_effect=Exception("offline"),
        ):
            response = client.post(
                "/context/search",
                json={"query": "adapter", "view": "current"},
                headers=self.headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["view"] == "current"
        assert data["results"][0]["path"] == "notes/mcp-adapter.md"
        assert "kb-api/2026-03-12" in data["results"][0]["sources"]

    def test_bundle_returns_excerpt_and_budgeted_content(self, client: TestClient, tmp_vault: Path):
        _commit_file(
            tmp_vault,
            "notes/context.md",
            "# Context Bundle\n\ncontext retrieval bundle\n",
            "add context",
        )
        _commit_file(
            tmp_vault,
            "notes/context-deep.md",
            "# Context Deep Dive\n\n" + "context " * 250,
            "add context deep",
        )

        response = client.post(
            "/context/bundle",
            json={"query": "context", "view": "main", "token_budget": 20},
            headers=self.headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["used_tokens"] <= 20
        assert any(item["content"] is not None for item in data["items"])
        assert any(item["truncated"] for item in data["items"])
