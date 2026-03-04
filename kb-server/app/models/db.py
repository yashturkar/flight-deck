from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True)
    job_type = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), default=utcnow)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error = Column(Text, nullable=True)
    meta = Column("meta", JSON, nullable=True)


class VaultEvent(Base):
    __tablename__ = "vault_events"

    id = Column(Integer, primary_key=True)
    event_type = Column(String(64), nullable=False)
    file_path = Column(String(1024), nullable=True)
    commit_sha = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    details = Column(JSON, nullable=True)


class PublishRun(Base):
    __tablename__ = "publish_runs"

    id = Column(Integer, primary_key=True)
    trigger = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False, default="pending")
    started_at = Column(DateTime(timezone=True), default=utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    commit_sha = Column(String(64), nullable=True)
    error = Column(Text, nullable=True)


def ensure_tables() -> None:
    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    session = SessionLocal()
    try:
        yield session  # type: ignore[misc]
    finally:
        session.close()
