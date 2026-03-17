"""Caller identity resolved from an authenticated API key."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.services.git_service import GitActor


@dataclass(frozen=True)
class CallerIdentity:
    """Identity attached to a request after API-key authentication."""

    key_id: int
    name: str
    role: Literal["readonly", "user", "agent", "admin"]
    prefix: str  # first 8 chars of key for logging

    @property
    def actor(self) -> GitActor:
        """Map role to git actor: user/admin → user, others → agent."""
        return "user" if self.role in ("user", "admin") else "agent"

    @property
    def can_write(self) -> bool:
        return self.role in ("user", "agent", "admin")
