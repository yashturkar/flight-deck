import os
import tempfile
from pathlib import Path

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///")
os.environ.setdefault("VAULT_PATH", "/tmp/kb-test-vault")


@pytest.fixture()
def tmp_vault(tmp_path: Path):
    """Create a temporary vault directory that is a git repo."""
    import subprocess

    vault = tmp_path / "vault"
    vault.mkdir()
    subprocess.run(["git", "init", str(vault)], check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.local"],
        cwd=vault,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=vault,
        check=True,
        capture_output=True,
    )
    # Initial commit so HEAD exists
    (vault / ".gitkeep").touch()
    subprocess.run(["git", "add", "."], cwd=vault, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=vault,
        check=True,
        capture_output=True,
    )
    return vault
