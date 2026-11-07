"""Create app_meta (schema and app version tracking).

Revision ID: 0001
Revises:
Create Date: 2026-11-07
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

SCHEMA_VERSION = 1


def upgrade() -> None:
    op.create_table(
        "app_meta",
        sa.Column("key", sa.String(length=64), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
    )
    op.execute(
        sa.text("INSERT INTO app_meta (key, value) VALUES ('schema_version', :v)").bindparams(
            v=str(SCHEMA_VERSION)
        )
    )


def downgrade() -> None:
    raise NotImplementedError("forward-only migrations; restore the pre-migration backup instead")
