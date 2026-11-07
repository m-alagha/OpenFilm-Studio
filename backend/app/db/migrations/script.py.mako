"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

${imports if imports else ""}
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = None
depends_on = None

# Each migration MUST bump app_meta.schema_version and app.db.migrate.SCHEMA_VERSION.
SCHEMA_VERSION = 0  # set to the new schema version


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    raise NotImplementedError("forward-only migrations; restore the pre-migration backup instead")
