"""Initial tables: jobs, vault_events, publish_runs

Revision ID: 001
Revises: None
Create Date: 2026-03-03
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("job_type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("meta", sa.JSON, nullable=True),
    )

    op.create_table(
        "vault_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("file_path", sa.String(1024), nullable=True),
        sa.Column("commit_sha", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("details", sa.JSON, nullable=True),
    )

    op.create_table(
        "publish_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("trigger", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("commit_sha", sa.String(64), nullable=True),
        sa.Column("error", sa.Text, nullable=True),
    )

    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_vault_events_type", "vault_events", ["event_type"])
    op.create_index("ix_publish_runs_status", "publish_runs", ["status"])


def downgrade() -> None:
    op.drop_table("publish_runs")
    op.drop_table("vault_events")
    op.drop_table("jobs")
