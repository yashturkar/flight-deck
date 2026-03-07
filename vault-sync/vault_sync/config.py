from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    kb_server_url: str = "http://localhost:8000"
    kb_api_key: str = ""
    sync_dir: Path = Path.home() / "vault-sync"
    sync_debounce_seconds: float = 2.0
    sync_pull_interval_seconds: float = 30.0


settings = Settings()
