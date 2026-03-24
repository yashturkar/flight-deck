from unittest.mock import MagicMock, patch

from app.services import github_service


class TestGitHubTokenSelection:
    def test_create_pr_uses_agent_token_when_configured(self):
        response = MagicMock()
        response.status_code = 201
        response.json.return_value = {"number": 7, "html_url": "https://example.test/pr/7"}

        client = MagicMock()
        client.__enter__.return_value = client
        client.post.return_value = response

        with patch("app.services.github_service.settings") as settings, \
             patch("app.services.github_service.httpx.Client", return_value=client):
            settings.github_agent_token = "agent-token"
            settings.github_token = "fallback-token"
            settings.github_repo = "owner/repo"
            settings.git_branch = "main"

            github_service.create_pr("kb-api/2026-03-11", "Title")

        assert client.post.call_args.kwargs["headers"]["Authorization"] == "Bearer agent-token"

    def test_create_pr_falls_back_to_legacy_token(self):
        response = MagicMock()
        response.status_code = 201
        response.json.return_value = {"number": 8, "html_url": "https://example.test/pr/8"}

        client = MagicMock()
        client.__enter__.return_value = client
        client.post.return_value = response

        with patch("app.services.github_service.settings") as settings, \
             patch("app.services.github_service.httpx.Client", return_value=client):
            settings.github_agent_token = ""
            settings.github_token = "fallback-token"
            settings.github_repo = "owner/repo"
            settings.git_branch = "main"

            github_service.create_pr("kb-api/2026-03-11", "Title")

        assert client.post.call_args.kwargs["headers"]["Authorization"] == "Bearer fallback-token"
