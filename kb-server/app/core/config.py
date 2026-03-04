from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    vault_path: Path = Path("/srv/flightdeck/vault")

    database_url: str = "postgresql://kb:kb@localhost:5432/kb"

    git_remote: str = "origin"
    git_branch: str = "main"
    git_push_enabled: bool = True

    autosave_debounce_seconds: int = 30

    quartz_build_command: str = ""
    quartz_webhook_url: str = ""

    api_host: str = "0.0.0.0"
    api_port: int = 8000


settings = Settings()
