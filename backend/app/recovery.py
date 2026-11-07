"""Recover from a failed update: list and restore verified database backups.

    python -m app.recovery list
    python -m app.recovery restore <backup-file-name> [--yes]

Restoring requires OpenFilm Studio to be closed (the data-directory lock), an
intact backup (checksum and integrity check), a schema this app can open, and
explicit confirmation. The current database is first saved as a new verified
backup, so a restore never destroys data. Other files are never touched.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sqlite3
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.config import ConfigError, load_settings
from app.datalock import DataDirLock, DataDirLockedError
from app.db.backup import BackupError, BackupResult, backup_database, sha256_file
from app.db.migrate import DatabaseCompatibilityError, check_compatibility
from app.integrity import changed_files, snapshot
from app.paths import DataDirError, prepare_data_dir

DB_NAME = "openfilm.sqlite"
SIDE_FILES = ("-journal", "-wal", "-shm")
_BACKUP_NAME = re.compile(r"^openfilm-[A-Za-z0-9_.-]{1,150}\.sqlite$")


class RecoveryError(Exception):
    pass


@dataclass(frozen=True)
class BackupInfo:
    name: str
    size: int
    verified: bool
    schema_version: int | None


def _schema_version(path: Path) -> int | None:
    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        row = conn.execute("SELECT value FROM app_meta WHERE key='schema_version'").fetchone()
        return int(row[0]) if row else None
    except sqlite3.DatabaseError:
        return None
    finally:
        conn.close()


def _verified(path: Path) -> bool:
    sidecar = path.with_name(path.name + ".sha256")
    if not sidecar.is_file():
        return False
    expected = sidecar.read_text(encoding="utf-8").split()[0]
    return expected == sha256_file(path)


def list_backups(data_dir: Path) -> list[BackupInfo]:
    backups = data_dir / "backups"
    if not backups.is_dir():
        return []
    return [
        BackupInfo(p.name, p.stat().st_size, _verified(p), _schema_version(p))
        for p in sorted(backups.glob("openfilm-*.sqlite"), reverse=True)
    ]


def preserve_current(db_path: Path, backups_dir: Path) -> BackupResult:
    """Save the current database before it is replaced.

    Normally a consistent SQLite backup with an integrity check. If the database is
    damaged (often the reason for restoring), its exact bytes are copied instead and
    the copy's SHA-256 is verified against the original, so nothing is lost either way.
    """
    try:
        return backup_database(db_path, backups_dir, "pre-restore")
    except (BackupError, sqlite3.DatabaseError):
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        target = backups_dir / f"openfilm-{stamp}-pre-restore-raw.sqlite"
        backups_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(db_path, target)
        digest = sha256_file(target)
        if digest != sha256_file(db_path):
            raise RecoveryError("could not make a verified copy of the current database") from None
        target.with_name(target.name + ".sha256").write_text(
            f"{digest}  {target.name}\n", encoding="utf-8"
        )
        return BackupResult(target, digest)


def restore_backup(data_dir: Path, name: str) -> BackupResult | None:
    """Restore ``backups/<name>`` over the database. Caller must hold the data lock."""
    if not _BACKUP_NAME.fullmatch(name):
        raise RecoveryError("invalid backup name")
    source = data_dir / "backups" / name
    if not source.is_file() or source.parent != data_dir / "backups":
        raise RecoveryError(f"backup {name} not found")
    if not _verified(source):
        raise RecoveryError("backup checksum does not match; it may be damaged")
    try:
        check_compatibility(source)
    except DatabaseCompatibilityError as exc:
        raise RecoveryError(f"this app cannot open that backup: {exc.message}") from exc

    db_path = data_dir / DB_NAME
    others_before = snapshot(data_dir)
    # Never overwrite without a verified safety copy of the current database.
    safety = preserve_current(db_path, data_dir / "backups") if db_path.is_file() else None

    # Build the restored database beside the original, verify it, then swap it in
    # with one atomic rename. A damaged current file is never written into.
    staged = data_dir / f"{DB_NAME}.restore-tmp"
    staged.unlink(missing_ok=True)  # only ever our own leftover temp file
    src = sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True)
    dest = sqlite3.connect(staged)
    try:
        src.backup(dest)
        result = dest.execute("PRAGMA integrity_check").fetchone()
    finally:
        dest.close()
        src.close()
    if result is None or result[0] != "ok":
        staged.unlink(missing_ok=True)
        saved = f"; your previous database is saved as {safety.path.name}" if safety else ""
        raise RecoveryError(f"restored database failed its integrity check{saved}")
    # Journal files belong to the old database; SQLite could replay them onto the
    # restored one. Move them next to the safety copy (never delete them).
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    keep = safety.path if safety else data_dir / "backups" / f"openfilm-{stamp}-orphaned.sqlite"
    for suffix in SIDE_FILES:
        side = db_path.with_name(DB_NAME + suffix)
        target = keep.with_name(keep.name + suffix)
        if side.exists() and not target.exists():  # never overwrite an earlier copy
            os.replace(side, target)
        elif side.exists():
            raise RecoveryError(f"cannot move aside {side.name}; the database was not replaced")
    os.replace(staged, db_path)
    diff = changed_files(others_before, snapshot(data_dir))
    unexpected = diff["removed"] + diff["modified"]
    if unexpected:  # only the new safety backup may appear
        raise RecoveryError(f"unexpected changes to user files: {unexpected}")
    return safety


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.recovery", description="List and restore database backups."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="list database backups")
    restore = sub.add_parser("restore", help="restore a database backup")
    restore.add_argument("name", help="backup file name, as shown by 'list'")
    restore.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    args = parser.parse_args(argv)

    try:
        data_dir = prepare_data_dir(load_settings().data_dir)
    except (ConfigError, DataDirError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.command == "list":
        backups = list_backups(data_dir)
        if not backups:
            print(f"No backups in {data_dir / 'backups'}")
        for b in backups:
            status = "verified" if b.verified else "UNVERIFIED"
            print(f"{b.name}  schema {b.schema_version}  {b.size} bytes  {status}")
        return 0

    if not args.yes:
        if not sys.stdin.isatty():
            print("error: confirmation required; re-run with --yes", file=sys.stderr)
            return 2
        print(f"This replaces the database in {data_dir} with backup {args.name}.")
        print("Your current database is saved as a new backup first. Media files are not touched.")
        if input("Type RESTORE to continue: ").strip() != "RESTORE":
            print("Cancelled. Nothing was changed.")
            return 1
    try:
        with DataDirLock(data_dir):
            safety = restore_backup(data_dir, args.name)
    except DataDirLockedError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3
    except RecoveryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    kept = f" Your previous database was saved as {safety.path.name}." if safety else ""
    print(f"Restored {args.name}.{kept}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
