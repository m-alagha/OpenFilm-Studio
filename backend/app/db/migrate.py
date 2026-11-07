"""Open the local database safely: compatibility check, backup, migrate.

Rules (CLAUDE.md, Update Safety Policy):
- A database written by a newer app (unknown revision or higher schema version)
  is refused and left byte-for-byte untouched.
- A database that is not an OpenFilm database is refused, never adopted.
- Before migrating an existing database, a verified backup is taken.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, text

from app import __version__
from app.db.backup import BackupResult, backup_database

logger = logging.getLogger(__name__)

# Highest schema version this app understands. Must equal the head migration's
# SCHEMA_VERSION (enforced by tests).
SCHEMA_VERSION = 2

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


class DatabaseCompatibilityError(Exception):
    """The database must not be opened by this app version."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class DatabaseStatus:
    schema_version: int
    created_by_app_version: str
    is_new: bool
    migrated_from_revision: str | None
    backup: BackupResult | None


@dataclass(frozen=True)
class _Inspection:
    is_empty: bool
    revision: str | None
    schema_version: int | None


def alembic_config() -> Config:
    config = Config()
    config.set_main_option("script_location", MIGRATIONS_DIR.as_posix())
    return config


def script_directory() -> ScriptDirectory:
    return ScriptDirectory.from_config(alembic_config())


def head_revision() -> str:
    head = script_directory().get_current_head()
    if head is None:
        raise RuntimeError("no migrations found")
    return head


def _inspect(db_path: Path) -> _Inspection:
    """Read-only inspection; never writes to the file."""
    if not db_path.exists() or db_path.stat().st_size == 0:
        return _Inspection(is_empty=True, revision=None, schema_version=None)
    try:
        conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        raise DatabaseCompatibilityError("DB_UNREADABLE", f"cannot open database: {exc}") from exc
    try:
        tables = {
            row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if not tables:
            return _Inspection(is_empty=True, revision=None, schema_version=None)
        if "alembic_version" not in tables:
            raise DatabaseCompatibilityError(
                "DB_UNRECOGNIZED",
                "this file is not an OpenFilm Studio database; it was not modified",
            )
        row = conn.execute("SELECT version_num FROM alembic_version").fetchone()
        revision = row[0] if row else None
        schema_version = None
        if "app_meta" in tables:
            meta = conn.execute("SELECT value FROM app_meta WHERE key='schema_version'").fetchone()
            schema_version = int(meta[0]) if meta else None
    except sqlite3.DatabaseError as exc:
        raise DatabaseCompatibilityError("DB_UNREADABLE", f"cannot read database: {exc}") from exc
    finally:
        conn.close()
    return _Inspection(is_empty=False, revision=revision, schema_version=schema_version)


def check_compatibility(db_path: Path) -> _Inspection:
    info = _inspect(db_path)
    if info.is_empty:
        return info
    known = {rev.revision for rev in script_directory().walk_revisions()}
    newer = (info.revision is not None and info.revision not in known) or (
        info.schema_version is not None and info.schema_version > SCHEMA_VERSION
    )
    if newer:
        raise DatabaseCompatibilityError(
            "DB_NEWER_SCHEMA",
            f"This data was created by a newer version of OpenFilm Studio "
            f"(schema {info.schema_version or 'unknown'}; this app supports up to "
            f"{SCHEMA_VERSION}). Update OpenFilm Studio to open it. "
            "Your data was not modified.",
        )
    return info


def _upgrade(engine: Engine) -> None:
    config = alembic_config()
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")


def _set_meta(engine: Engine, key: str, value: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO app_meta (key, value) VALUES (:k, :v) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value"
            ),
            {"k": key, "v": value},
        )


def _get_meta(engine: Engine, key: str) -> str | None:
    with engine.connect() as conn:
        value = conn.execute(text("SELECT value FROM app_meta WHERE key=:k"), {"k": key}).scalar()
    return None if value is None else str(value)


def open_database(engine: Engine, db_path: Path, backups_dir: Path) -> DatabaseStatus:
    info = check_compatibility(db_path)
    head = head_revision()
    backup: BackupResult | None = None
    migrated_from: str | None = None

    if not info.is_empty and info.revision != head:
        migrated_from = info.revision
        backup = backup_database(db_path, backups_dir, f"pre-migrate-{info.revision}-to-{head}")
        logger.info("verified backup %s before migrating", backup.path.name)

    if info.is_empty or info.revision != head:
        _upgrade(engine)

    now = datetime.now(UTC).isoformat()
    if info.is_empty:
        _set_meta(engine, "created_by_app_version", __version__)
        _set_meta(engine, "created_at", now)
    _set_meta(engine, "last_opened_app_version", __version__)
    _set_meta(engine, "last_opened_at", now)

    schema = _get_meta(engine, "schema_version")
    if schema is None or int(schema) != SCHEMA_VERSION:
        raise RuntimeError(f"schema_version {schema} after migration, expected {SCHEMA_VERSION}")
    return DatabaseStatus(
        schema_version=int(schema),
        created_by_app_version=_get_meta(engine, "created_by_app_version") or "unknown",
        is_new=info.is_empty,
        migrated_from_revision=migrated_from,
        backup=backup,
    )
