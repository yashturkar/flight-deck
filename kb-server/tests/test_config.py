from pathlib import Path

from app.core.config import Settings


def test_environment_variables_override_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "KB_API_KEY=from-env-file",
                "GITHUB_TOKEN=from-env-file",
                "VAULT_PATH=/tmp/from-env-file",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("KB_API_KEY", "from-environment")
    monkeypatch.setenv("GITHUB_TOKEN", "from-environment")
    monkeypatch.setenv("VAULT_PATH", "/tmp/from-environment")

    settings = Settings(_env_file=env_file)

    assert settings.kb_api_key == "from-environment"
    assert settings.github_token == "from-environment"
    assert settings.vault_path == Path("/tmp/from-environment")
