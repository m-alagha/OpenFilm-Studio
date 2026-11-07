"""Create app_settings (user-visible settings; never credentials).

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-07
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

SCHEMA_VERSION = 2


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=128), primary_key=True),
        sa.Column("value_json", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute(
        sa.text("UPDATE app_meta SET value = :v WHERE key = 'schema_version'").bindparams(
            v=str(SCHEMA_VERSION)
        )
    )


def downgrade() -> None:
    raise NotImplementedError("forward-only migrations; restore the pre-migration backup instead")
