"""Alembic environment. Migrations run programmatically from app.db.migrate."""

from __future__ import annotations

from alembic import context
from sqlalchemy import Connection

from app.db.models import Base

target_metadata = Base.metadata


def run_migrations_online() -> None:
    connection: Connection | None = context.config.attributes.get("connection")
    if connection is None:
        raise RuntimeError("run migrations through app.db.migrate, not the alembic CLI")
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
        transactional_ddl=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    raise RuntimeError("offline migrations are not supported")
run_migrations_online()
