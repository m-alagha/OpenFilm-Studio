"""ORM models. Schema changes require a new Alembic migration in db/migrations."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class AppMeta(Base):
    """Key/value facts about this database (schema version, app versions)."""

    __tablename__ = "app_meta"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)


class AppSetting(Base):
    """User-visible application settings. Never holds credentials."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value_json: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UpdateState(Base):
    """Single-row update-manager state (id is always 1). Never holds credentials."""

    __tablename__ = "update_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    auto_check_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    disclosure_acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_check_status: Mapped[str | None] = mapped_column(String(32))
    retry_not_before: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    latest_release_json: Mapped[str | None] = mapped_column(Text)
    skipped_version: Mapped[str | None] = mapped_column(String(64))
    snoozed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
