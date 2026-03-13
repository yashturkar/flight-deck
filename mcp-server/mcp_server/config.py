from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MCPServerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    kb_server_url: str = "http://127.0.0.1:8000"
    kb_api_key: str = ""
    mcp_default_view: str = "current"
    mcp_default_limit: int = Field(default=10, ge=1, le=50)
    mcp_default_token_budget: int = Field(default=4000, ge=1, le=50000)
    mcp_transport: str = "stdio"
