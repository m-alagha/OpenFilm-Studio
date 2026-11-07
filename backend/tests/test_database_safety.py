"""M1.5 final review: database safety regressions.

- No network request runs inside a SQLite write transaction.
- Concurrent update checks cannot deadlock the database.
- The data-folder lock is released after a normal shutdown and after a crash.
- Recovery never overwrites a database without a verified safety copy.
"""

from __future__ import annotations

import sqlite3
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
from conftest import FakeFetcher, release_json
from fastapi.testclient import TestClient

from app import recovery
from app.config import Settings
from app.datalock import DataDirLock, DataDirLockedError
from app.db.backup import backup_database, sha256_file
from app.db.engine import make_engine
from app.db.migrate import open_database
from app.main import create_app
from app.updates.install import InstallInfo, InstallType
from app.updates.service import UpdateService

BACKEND_DIR = Path(__file__).resolve().parents[1]


def make_service(tmp_path: Path, fetcher: object) -> tuple[UpdateService, Path]:
    db = tmp_path / "openfilm.sqlite"
    (tmp_path / "backups").mkdir(parents=True, exist_ok=True)
    engine = make_engine(db)
    open_database(engine, db, tmp_path / "backups")
    install = InstallInfo(InstallType.GIT, "linux", tmp_path)
    return UpdateService(engine, "0.1.0", install, fetcher), db  # type: ignore[arg-type]


def assert_db_writable_now(db: Path) -> None:
    """Fails immediately (timeout=0) if any connection holds a write transaction."""
    conn = sqlite3.connect(db, timeout=0, isolation_level=None)
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("UPDATE app_meta SET value = value WHERE key = 'schema_version'")
        conn.execute("ROLLBACK")
    finally:
        conn.close()


# --- no network inside write transactions ---------------------------------------


@pytest.mark.parametrize("manual", [True, False])
def test_fetch_runs_with_no_database_transaction_open(tmp_path: Path, manual: bool) -> None:
    observed: list[str] = []
    db_holder: list[Path] = []

    def fetch() -> bytes:
        try:
            assert_db_writable_now(db_holder[0])
            observed.append("free")
        except sqlite3.OperationalError as exc:
            observed.append(f"locked: {exc}")
        return b"[]"

    service, db = make_service(tmp_path, fetch)
    db_holder.append(db)
    service.set_preferences(disclosure_acknowledged=True)
    service.check(manual=manual)
    assert observed == ["free"]


def test_api_check_runs_with_no_database_transaction_open(settings: Settings) -> None:
    observed: list[str] = []

    def fetch() -> bytes:
        try:
            assert_db_writable_now(settings.db_path)
            observed.append("free")
        except sqlite3.OperationalError as exc:
            observed.append(f"locked: {exc}")
        return b"[]"

    install = InstallInfo(InstallType.GIT, "linux", Path("/opt/openfilm"))
    with TestClient(
        create_app(settings, release_fetcher=fetch, install=install), base_url="http://127.0.0.1"
    ) as client:
        response = client.post("/api/updates/check", headers={"X-OpenFilm-Client": "web"})
    assert response.status_code == 200
    assert observed == ["free"]


# --- concurrency ------------------------------------------------------------------


def test_concurrent_update_checks_never_deadlock_and_fetch_serially(tmp_path: Path) -> None:
    active = 0
    peak = 0
    guard = threading.Lock()

    def slow_fetch() -> bytes:
        nonlocal active, peak
        with guard:
            active += 1
            peak = max(peak, active)
        time.sleep(0.02)
        with guard:
            active -= 1
        return b"[]"

    service, _ = make_service(tmp_path, slow_fetch)
    service.set_preferences(disclosure_acknowledged=True)
    errors: list[BaseException] = []

    def checker(manual: bool) -> None:
        try:
            for _ in range(3):
                service.check(manual=manual)
        except BaseException as exc:  # noqa: BLE001 - collected for the assertion
            errors.append(exc)

    def reader() -> None:
        try:
            for _ in range(20):
                service.status()
                service.should_auto_check()
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=checker, args=(i % 2 == 0,)) for i in range(6)]
    threads += [threading.Thread(target=reader) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    assert not any(t.is_alive() for t in threads), "deadlock: a thread did not finish"
    assert errors == []
    assert peak == 1  # one network check at a time


def test_background_loop_and_manual_checks_together(settings: Settings) -> None:
    import dataclasses

    fetcher = FakeFetcher([release_json("v0.2.0")])
    install = InstallInfo(InstallType.GIT, "linux", Path("/opt/openfilm"))
    with TestClient(create_app(settings, install=install), base_url="http://127.0.0.1") as c:
        c.put("/api/updates/preferences", json={"disclosure_acknowledged": True},
              headers={"X-OpenFilm-Client": "web"})  # fmt: skip
    fast = dataclasses.replace(settings, update_initial_delay_s=0, update_poll_interval_s=0.01)
    statuses: list[int] = []
    with TestClient(
        create_app(fast, release_fetcher=fetcher, install=install), base_url="http://127.0.0.1"
    ) as client:

        def hammer() -> None:
            for _ in range(10):
                statuses.append(
                    client.post(
                        "/api/updates/check", headers={"X-OpenFilm-Client": "web"}
                    ).status_code
                )
                statuses.append(client.get("/api/updates").status_code)

        threads = [threading.Thread(target=hammer) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)
    assert statuses and set(statuses) == {200}


# --- lock release -----------------------------------------------------------------


def test_lock_released_after_normal_app_shutdown(settings: Settings) -> None:
    client = TestClient(create_app(settings), base_url="http://127.0.0.1")
    with client, pytest.raises(DataDirLockedError):
        DataDirLock(settings.data_dir).acquire()  # held while the app runs
    with DataDirLock(settings.data_dir) as lock:  # released by the lifespan
        assert lock.held


def test_lock_released_when_process_exits_normally(tmp_path: Path) -> None:
    code = (
        "import sys; from pathlib import Path; from app.datalock import DataDirLock; "
        "held = DataDirLock(Path(sys.argv[1])).acquire(); print('ok')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code, str(tmp_path)], cwd=BACKEND_DIR, capture_output=True,
        text=True, timeout=30, check=True,
    )  # fmt: skip
    assert result.stdout.strip() == "ok"
    with DataDirLock(tmp_path) as lock:  # exit without release() still frees it
        assert lock.held


# --- recovery safety copy ------------------------------------------------------------


def make_data(tmp_path: Path) -> tuple[Path, Path]:
    data = tmp_path / "data"
    (data / "backups").mkdir(parents=True)
    db = data / "openfilm.sqlite"
    engine = make_engine(db)
    open_database(engine, db, data / "backups")
    engine.dispose()
    return data, db


def test_restore_aborts_without_touching_db_if_safety_copy_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data, db = make_data(tmp_path)
    backup = backup_database(db, data / "backups", "target")
    conn = sqlite3.connect(db)
    conn.execute("INSERT INTO app_meta (key, value) VALUES ('newer', 'data')")
    conn.commit()
    conn.close()
    before = sha256_file(db)

    def broken(*args: object, **kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(recovery, "backup_database", broken)
    monkeypatch.setattr("app.recovery.shutil.copy2", broken)
    with pytest.raises(OSError, match="disk full"):
        recovery.restore_backup(data, backup.path.name)
    assert sha256_file(db) == before  # current database never overwritten


def test_corrupt_current_db_is_preserved_byte_for_byte_before_restore(tmp_path: Path) -> None:
    data, db = make_data(tmp_path)
    backup = backup_database(db, data / "backups", "good")
    corrupt = b"SQLite format 3\x00" + b"\xde\xad" * 5000
    db.write_bytes(corrupt)

    safety = recovery.restore_backup(data, backup.path.name)

    assert safety is not None
    assert safety.path.read_bytes() == corrupt  # nothing lost, even when damaged
    sidecar = safety.path.with_name(safety.path.name + ".sha256").read_text(encoding="utf-8")
    assert sidecar.split()[0] == sha256_file(safety.path)
    conn = sqlite3.connect(db)
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    conn.close()


def test_safety_copy_is_verified(tmp_path: Path) -> None:
    data, db = make_data(tmp_path)
    backup = backup_database(db, data / "backups", "target")
    safety = recovery.restore_backup(data, backup.path.name)
    assert safety is not None
    assert recovery._verified(safety.path)


def test_leftover_journal_is_moved_aside_not_replayed_or_deleted(tmp_path: Path) -> None:
    data, db = make_data(tmp_path)
    backup = backup_database(db, data / "backups", "good")
    journal = db.with_name("openfilm.sqlite-journal")
    journal.write_bytes(b"stale hot journal from a crash")

    safety = recovery.restore_backup(data, backup.path.name)

    assert safety is not None
    assert not journal.exists()
    moved = safety.path.with_name(safety.path.name + "-journal")
    assert moved.read_bytes() == b"stale hot journal from a crash"
    assert not (data / "openfilm.sqlite.restore-tmp").exists()
