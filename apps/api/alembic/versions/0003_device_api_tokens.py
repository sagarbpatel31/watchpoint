"""Add device API token hash for ingest auth.

Revision ID: 0003_device_api_tokens
Revises: 0002
Create Date: 2026-06-10
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_device_api_tokens"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "devices",
        sa.Column("api_token_hash", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_devices_api_token_hash", "devices", ["api_token_hash"])


def downgrade() -> None:
    op.drop_index("ix_devices_api_token_hash", table_name="devices")
    op.drop_column("devices", "api_token_hash")
