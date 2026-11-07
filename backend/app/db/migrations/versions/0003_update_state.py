"""Create update_state (update-manager preferences and last check result).

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-07
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

SCHEMA_VERSION = 3


def upgrade() -> None:
    op.create_table(
        "update_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("auto_check_enabled", sa.Boolean(), nullable=False),
        sa.Column("disclosure_acknowledged", sa.Boolean(), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_check_status", sa.String(length=32), nullable=True),
        sa.Column("retry_not_before", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latest_release_json", sa.Text(), nullable=True),
        sa.Column("skipped_version", sa.String(length=64), nullable=True),
        sa.Column("snoozed_until", sa.DateTime(timezone=True), nullable=True),
    )
    # D8 defaults: checks on, but nothing runs until the first-run disclosure is seen.
    op.execute(
        "INSERT INTO update_state (id, auto_check_enabled, disclosure_acknowledged) "
        "VALUES (1, 1, 0)"
    )
    op.execute(
        sa.text("UPDATE app_meta SET value = :v WHERE key = 'schema_version'").bindparams(
            v=str(SCHEMA_VERSION)
        )
    )


def downgrade() -> None:
    raise NotImplementedError("forward-only migrations; restore the pre-migration backup instead")
