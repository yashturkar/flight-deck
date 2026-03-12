from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    vault_path: Path = Path("/srv/flightdeck/vault")
    database_url: str = "postgresql://kb:kb@localhost:5432/kb"
    kb_api_key: str = ""  # Deprecated fallback; prefer DB-backed keys via app.cli.keys

    # Git settings
    git_remote: str = "origin"
    git_branch: str = "main"
    git_push_enabled: bool = True
    git_user_author_name: str = ""
    git_user_author_email: str = ""
    git_user_committer_name: str = ""
    git_user_committer_email: str = ""
    git_user_ssh_command: str = ""
    git_agent_author_name: str = ""
    git_agent_author_email: str = ""
    git_agent_committer_name: str = ""
    git_agent_committer_email: str = ""
    git_agent_ssh_command: str = ""
    git_agent_https_token: str = ""  # PAT used for agent git push over HTTPS

    # API write batching - commits go to a daily branch and create/update a PR
    git_batch_debounce_seconds: int = 10
    git_batch_branch_prefix: str = "kb-api"

    # GitHub API for PR creation (required for API write workflow)
    github_token: str = ""
    github_agent_token: str = ""
    github_repo: str = ""  # e.g., "owner/repo"

    # Autosave (file watcher) settings
    autosave_debounce_seconds: int = 30
    git_pull_interval_seconds: int = 60

    quartz_build_command: str = ""
    quartz_webhook_url: str = ""
    api_host: str = "0.0.0.0"
    api_port: int = 8000


settings = Settings()
