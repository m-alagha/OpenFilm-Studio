from __future__ import annotations

import importlib.util
import shutil
import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Engine, text

from app import __version__
from app.db import migrate
from app.db.backup import sha256_file
from app.db.engine import make_engine
from app.db.migrate import (
    SCHEMA_VERSION,
    DatabaseCompatibilityError,
    alembic_config,
    head_revision,
    open_database,
)
from app.db.models import Base


@pytest.fixture
def db(tmp_path: Path) -> tuple[Engine, Path, Path]:
    backups = tmp_path / "backups"
    backups.mkdir()
    path = tmp_path / "openfilm.sqlite"
    return make_engine(path), path, backups


def upgrade_to(engine: Engine, revision: str) -> None:
    config = alembic_config()
    with engine.begin() as conn:
        config.attributes["connection"] = conn
        command.upgrade(config, revision)


def meta(path: Path, key: str) -> str | None:
    conn = sqlite3.connect(path)
    try:
        row = conn.execute("SELECT value FROM app_meta WHERE key=?", (key,)).fetchone()
    finally:
        conn.close()
    return None if row is None else str(row[0])


def test_head_migration_matches_schema_version() -> None:
    versions = migrate.MIGRATIONS_DIR / "versions"
    head = head_revision()
    (module_file,) = versions.glob(f"{head}_*.py")
    spec = importlib.util.spec_from_file_location("head_migration", module_file)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.SCHEMA_VERSION == SCHEMA_VERSION


def test_models_match_migrations(db: tuple[Engine, Path, Path]) -> None:
    engine, _path, _backups = db
    upgrade_to(engine, "head")
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == []


def test_new_database_is_created_at_head(db: tuple[Engine, Path, Path]) -> None:
    engine, path, backups = db
    status = open_database(engine, path, backups)
    assert status.is_new
    assert status.schema_version == SCHEMA_VERSION
    assert status.backup is None
    assert meta(path, "created_by_app_version") == __version__
    assert meta(path, "last_opened_app_version") == __version__
    assert list(backups.iterdir()) == []


def test_reopen_at_head_is_noop(db: tuple[Engine, Path, Path]) -> None:
    engine, path, backups = db
    open_database(engine, path, backups)
    status = open_database(engine, path, backups)
    assert not status.is_new
    assert status.migrated_from_revision is None
    assert list(backups.iterdir()) == []


def test_upgrade_takes_verified_backup_and_preserves_data(
    db: tuple[Engine, Path, Path],
) -> None:
    engine, path, backups = db
    upgrade_to(engine, "0001")
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO app_meta (key, value) VALUES ('probe', 'kept')"))
    engine.dispose()

    status = open_database(engine, path, backups)

    assert status.migrated_from_revision == "0001"
    assert status.backup is not None
    assert status.backup.sha256 == sha256_file(status.backup.path)
    checksum_file = status.backup.path.with_name(status.backup.path.name + ".sha256")
    assert checksum_file.read_text(encoding="utf-8").startswith(status.backup.sha256)
    # The backup is the pre-migration database.
    assert meta(status.backup.path, "schema_version") == "1"
    assert meta(status.backup.path, "probe") == "kept"
    # The live database was migrated and kept its data.
    assert meta(path, "schema_version") == str(SCHEMA_VERSION)
    assert meta(path, "probe") == "kept"


def _sabotage(path: Path, sql: str) -> str:
    conn = sqlite3.connect(path)
    try:
        conn.execute(sql)
        conn.commit()
    finally:
        conn.close()
    return sha256_file(path)


@pytest.mark.parametrize(
    ("sql", "code"),
    [
        ("UPDATE alembic_version SET version_num = '9999'", "DB_NEWER_SCHEMA"),
        (
            f"UPDATE app_meta SET value = '{SCHEMA_VERSION + 1}' WHERE key = 'schema_version'",
            "DB_NEWER_SCHEMA",
        ),
        ("DROP TABLE alembic_version", "DB_UNRECOGNIZED"),
    ],
)
def test_incompatible_database_is_refused_untouched(
    db: tuple[Engine, Path, Path], sql: str, code: str
) -> None:
    engine, path, backups = db
    open_database(engine, path, backups)
    engine.dispose()
    before = _sabotage(path, sql)

    with pytest.raises(DatabaseCompatibilityError) as info:
        open_database(engine, path, backups)

    assert info.value.code == code
    assert "not modified" in info.value.message
    assert sha256_file(path) == before
    assert list(backups.iterdir()) == []


def test_foreign_sqlite_file_is_refused(db: tuple[Engine, Path, Path]) -> None:
    engine, path, backups = db
    before = _sabotage(path, "CREATE TABLE photos (id INTEGER PRIMARY KEY)")
    with pytest.raises(DatabaseCompatibilityError) as info:
        open_database(engine, path, backups)
    assert info.value.code == "DB_UNRECOGNIZED"
    assert sha256_file(path) == before


def test_corrupt_file_is_refused(db: tuple[Engine, Path, Path]) -> None:
    engine, path, backups = db
    path.write_bytes(b"this is not a database" * 100)
    with pytest.raises(DatabaseCompatibilityError) as info:
        open_database(engine, path, backups)
    assert info.value.code == "DB_UNREADABLE"


FAILING_MIGRATION = """
import sqlalchemy as sa
from alembic import op

revision = "9999"
down_revision = "{head}"
branch_labels = None
depends_on = None
SCHEMA_VERSION = {next_schema}


def upgrade() -> None:
    op.create_table("half_done", sa.Column("id", sa.Integer(), primary_key=True))
    op.execute("UPDATE app_meta SET value = '{next_schema}' WHERE key = 'schema_version'")
    raise RuntimeError("simulated migration failure")


def downgrade() -> None:
    raise NotImplementedError
"""


def test_failed_migration_rolls_back_and_keeps_backup(
    db: tuple[Engine, Path, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine, path, backups = db
    open_database(engine, path, backups)
    engine.dispose()
    before = sha256_file(path)

    migrations = tmp_path / "migrations"
    shutil.copytree(migrate.MIGRATIONS_DIR, migrations)
    head = head_revision()  # the real head, before the failing migration is added
    failing = FAILING_MIGRATION.format(head=head, next_schema=SCHEMA_VERSION + 1)
    (migrations / "versions" / "9999_failing.py").write_text(failing, encoding="utf-8")
    monkeypatch.setattr(migrate, "MIGRATIONS_DIR", migrations)
    monkeypatch.setattr(migrate, "SCHEMA_VERSION", SCHEMA_VERSION + 1)

    with pytest.raises(RuntimeError, match="simulated migration failure"):
        open_database(engine, path, backups)
    engine.dispose()

    # Transactional DDL: nothing from the failed migration was applied.
    conn = sqlite3.connect(path)
    try:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        version = conn.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    finally:
        conn.close()
    assert "half_done" not in tables
    assert version == head
    assert meta(path, "schema_version") == str(SCHEMA_VERSION)
    assert sha256_file(path) == before
    # A verified pre-migration backup exists for recovery.
    (backup,) = backups.glob("*.sqlite")
    assert meta(backup, "schema_version") == str(SCHEMA_VERSION)
