"""Add device_tokens table for agent authentication

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-06

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "device_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("device_id", UUID(as_uuid=True), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("token_prefix", sa.String(16), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_device_tokens_device_id", "device_tokens", ["device_id"])
    op.create_index("ix_device_tokens_token_prefix", "device_tokens", ["token_prefix"])
    # Unique: the hash is the lookup key on the ingest hot path.
    op.create_index("ix_device_tokens_token_hash", "device_tokens", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_table("device_tokens")
