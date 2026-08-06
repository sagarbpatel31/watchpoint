"""Align users.email and workspaces.slug indexes with the models

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-06

`0001_initial` created a plain index plus a separate UNIQUE constraint for these
columns, while the models declare `unique=True, index=True` — which SQLAlchemy
expresses as a single unique index. Uniqueness was correctly enforced either
way, so this is not a data-integrity fix; it removes a redundant index and makes
`alembic check` clean, so genuine model drift is visible instead of buried under
permanent noise.

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # users.email
    op.drop_constraint("users_email_key", "users", type_="unique")
    op.drop_index("ix_users_email", table_name="users")
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # workspaces.slug
    op.drop_constraint("workspaces_slug_key", "workspaces", type_="unique")
    op.drop_index("ix_workspaces_slug", table_name="workspaces")
    op.create_index("ix_workspaces_slug", "workspaces", ["slug"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_workspaces_slug", table_name="workspaces")
    op.create_index("ix_workspaces_slug", "workspaces", ["slug"])
    op.create_unique_constraint("workspaces_slug_key", "workspaces", ["slug"])

    op.drop_index("ix_users_email", table_name="users")
    op.create_index("ix_users_email", "users", ["email"])
    op.create_unique_constraint("users_email_key", "users", ["email"])
