"""Data-directory lock, backup recovery and user-data preservation across updates."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.datalock import LOCK_NAME, DataDirLock, DataDirLockedError
from app.db.backup import backup_database, sha256_file
from app.db.engine import make_engine
from app.db.migrate import SCHEMA_VERSION, alembic_config, open_database
from app.integrity import changed_files, snapshot
from app.main import create_app
from app.recovery import RecoveryError, list_backups, restore_backup
from app.recovery import main as recovery_main
from app.updates.install import InstallInfo, InstallType

BACKEND_DIR = Path(__file__).resolve().parents[1]

# --- lock -------------------------------------------------------------------------


def test_lock_is_exclusive_and_reusable(tmp_path: Path) -> None:
    first = DataDirLock(tmp_path).acquire()
    with pytest.raises(DataDirLockedError, match="already running"):
        DataDirLock(tmp_path).acquire()
    first.release()
    assert json.loads((tmp_path / LOCK_NAME).read_text())["pid"] == os.getpid()  # informational
    with DataDirLock(tmp_path) as again:
        assert again.held
    assert (tmp_path / LOCK_NAME).exists()  # never deleted


def test_app_will_not_open_a_locked_data_dir(settings: Settings) -> None:
    settings.data_dir.mkdir(parents=True)
    client = TestClient(create_app(settings), base_url="http://127.0.0.1")
    with DataDirLock(settings.data_dir), pytest.raises(DataDirLockedError), client:
        pass
    assert not settings.db_path.exists()  # no DB created or migrated while locked


def test_lock_released_when_holder_process_dies(tmp_path: Path) -> None:
    holder = subprocess.Popen(
        [sys.executable, "-c",
         "import sys, time; from pathlib import Path; from app.datalock import DataDirLock; "
         # Keep a reference: a garbage-collected lock object would release the lock.
         "held = DataDirLock(Path(sys.argv[1])).acquire(); "
         "print('locked', flush=True); time.sleep(60)",
         str(tmp_path)],
        cwd=BACKEND_DIR, stdout=subprocess.PIPE, text=True,
    )  # fmt: skip
    try:
        assert holder.stdout is not None and holder.stdout.readline().strip() == "locked"
        with pytest.raises(DataDirLockedError):
            DataDirLock(tmp_path).acquire()
        holder.kill()  # simulate a crash: no clean release
        holder.wait(timeout=10)
        deadline = time.monotonic() + 5
        while True:
            try:
                DataDirLock(tmp_path).acquire().release()
                break
            except DataDirLockedError:
                if time.monotonic() > deadline:
                    raise
                time.sleep(0.1)
    finally:
        holder.kill()
        holder.wait(timeout=10)


# --- recovery ---------------------------------------------------------------------


def make_data_dir(root: Path, revision: str = "head") -> Path:
    data = root / "data"
    for sub in ("backups", "media/characters", "logs"):
        (data / sub).mkdir(parents=True, exist_ok=True)
    engine = make_engine(data / "openfilm.sqlite")
    if revision == "head":
        open_database(engine, data / "openfilm.sqlite", data / "backups")
    else:
        from alembic import command

        config = alembic_config()
        with engine.begin() as conn:
            config.attributes["connection"] = conn
            command.upgrade(config, revision)
    engine.dispose()
    (data / "media" / "characters" / "hero.png").write_bytes(b"\x89PNG fake reference image")
    (data / "media" / "scene-01.mp4").write_bytes(b"fake generated video" * 100)
    return data


def set_welcome(db: Path, value: str) -> None:
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO app_settings (key, value_json, updated_at) VALUES ('ui.welcome_dismissed', ?, "
        "'2026-11-07') ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json",
        (value,),
    )
    conn.commit()
    conn.close()


def get_welcome(db: Path) -> str | None:
    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT value_json FROM app_settings WHERE key='ui.welcome_dismissed'"
    ).fetchone()
    conn.close()
    return None if row is None else str(row[0])


def test_restore_reverts_db_keeps_safety_copy_and_media(tmp_path: Path) -> None:
    data = make_data_dir(tmp_path)
    db = data / "openfilm.sqlite"
    set_welcome(db, "false")
    backup = backup_database(db, data / "backups", "manual")
    set_welcome(db, "true")
    media_before = snapshot(data)

    safety = restore_backup(data, backup.path.name)

    assert get_welcome(db) == "false"
    assert safety is not None and get_welcome(safety.path) == "true"  # nothing lost
    diff = changed_files(media_before, snapshot(data))
    assert diff["removed"] == [] and diff["modified"] == []
    assert all(name.startswith("backups/") for name in diff["added"])
    names = [b.name for b in list_backups(data)]
    assert backup.path.name in names and safety.path.name in names
    assert all(b.verified for b in list_backups(data))


@pytest.mark.parametrize(
    "name",
    ["../openfilm.sqlite", "/etc/passwd", "openfilm-x.sqlite/../../y", "C:\\x.sqlite", "notes.txt",
     "openfilm-missing.sqlite", "openfilm-x.sqlite\n"],
)  # fmt: skip
def test_restore_rejects_bad_names(tmp_path: Path, name: str) -> None:
    data = make_data_dir(tmp_path)
    before = sha256_file(data / "openfilm.sqlite")
    with pytest.raises(RecoveryError):
        restore_backup(data, name)
    assert sha256_file(data / "openfilm.sqlite") == before


def test_restore_rejects_damaged_and_newer_backups(tmp_path: Path) -> None:
    data = make_data_dir(tmp_path)
    db = data / "openfilm.sqlite"
    damaged = backup_database(db, data / "backups", "damaged")
    with damaged.path.open("ab") as fh:
        fh.write(b"tamper")
    with pytest.raises(RecoveryError, match="checksum"):
        restore_backup(data, damaged.path.name)

    newer = backup_database(db, data / "backups", "newer")
    conn = sqlite3.connect(newer.path)
    conn.execute("UPDATE alembic_version SET version_num = 'future'")
    conn.commit()
    conn.close()
    newer.path.with_name(newer.path.name + ".sha256").write_text(
        f"{sha256_file(newer.path)}  {newer.path.name}\n", encoding="utf-8"
    )
    with pytest.raises(RecoveryError, match="cannot open"):
        restore_backup(data, newer.path.name)


def test_recovery_cli_requires_confirmation_and_the_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    data = make_data_dir(tmp_path)
    backup = backup_database(data / "openfilm.sqlite", data / "backups", "cli")
    monkeypatch.setenv("OPENFILM_DATA_DIR", str(data))
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)

    assert recovery_main(["list"]) == 0
    assert backup.path.name in capsys.readouterr().out
    assert recovery_main(["restore", backup.path.name]) == 2  # no --yes, not interactive
    with DataDirLock(data):
        assert recovery_main(["restore", backup.path.name, "--yes"]) == 3  # app running
    assert recovery_main(["restore", backup.path.name, "--yes"]) == 0


# --- data preservation across an update --------------------------------------------


def test_update_preserves_user_data_and_can_roll_back(tmp_path: Path) -> None:
    """M1 data folder (schema 2) opened by this version (schema 3), then rolled back."""
    data = make_data_dir(tmp_path, revision="0002")
    db = data / "openfilm.sqlite"
    set_welcome(db, "true")
    files_before = snapshot(data)

    settings = Settings(data_dir=data)
    install = InstallInfo(InstallType.GIT, "windows", tmp_path)
    with TestClient(create_app(settings, install=install), base_url="http://127.0.0.1") as client:
        assert client.get("/api/system").json()["schema_version"] == SCHEMA_VERSION
        assert client.get("/api/settings").json() == {"ui.welcome_dismissed": True}

    diff = changed_files(files_before, snapshot(data))
    assert diff["removed"] == [] and diff["modified"] == []  # media untouched
    (pre_migration,) = [b for b in list_backups(data) if "pre-migrate-0002" in b.name]
    assert pre_migration.verified and pre_migration.schema_version == 2
    assert get_welcome(db) == "true"

    # Rollback: restore the pre-migration backup for the previous app version.
    restore_backup(data, pre_migration.name)
    conn = sqlite3.connect(db)
    version = conn.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    conn.close()
    assert version == "0002"
    assert get_welcome(db) == "true"
    diff = changed_files(files_before, snapshot(data))
    assert diff["removed"] == [] and diff["modified"] == []
