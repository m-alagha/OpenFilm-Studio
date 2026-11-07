"""Consistent, verified SQLite backups (taken before every migration)."""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


class BackupError(Exception):
    pass


@dataclass(frozen=True)
class BackupResult:
    path: Path
    sha256: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def backup_database(db_path: Path, backups_dir: Path, reason: str) -> BackupResult:
    """Copy the DB with SQLite's online backup API, then verify the copy."""
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    safe_reason = "".join(c if c.isalnum() or c in "-_" else "-" for c in reason)[:60]
    target = backups_dir / f"openfilm-{stamp}-{safe_reason}.sqlite"
    backups_dir.mkdir(parents=True, exist_ok=True)

    source = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    dest = sqlite3.connect(target)
    try:
        source.backup(dest)
    finally:
        dest.close()
        source.close()

    verify = sqlite3.connect(f"file:{target.as_posix()}?mode=ro", uri=True)
    try:
        result = verify.execute("PRAGMA integrity_check").fetchone()
    finally:
        verify.close()
    if result is None or result[0] != "ok":
        raise BackupError(f"backup {target.name} failed integrity check")

    digest = sha256_file(target)
    target.with_name(target.name + ".sha256").write_text(
        f"{digest}  {target.name}\n", encoding="utf-8"
    )
    return BackupResult(target, digest)
