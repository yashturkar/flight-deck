"""SQLAlchemy model for hashed API keys."""

from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String

from app.models.db import Base, utcnow


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True)
    key_hash = Column(String(128), unique=True, nullable=False, index=True)
    prefix = Column(String(12), nullable=False)
    name = Column(String(128), nullable=False)
    role = Column(String(32), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    meta = Column(JSON, nullable=True)
