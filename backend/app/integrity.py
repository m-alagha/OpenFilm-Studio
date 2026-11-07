"""Data-preservation verification: fingerprint the user-data directory.

Used to prove that updates, migrations and restores leave user files untouched.
The database is compared separately by rows, because a verified migration is
allowed to change it; logs and the lock file are excluded as volatile.
"""

from __future__ import annotations

from pathlib import Path

from app.datalock import LOCK_NAME
from app.db.backup import sha256_file

VOLATILE_DIRS = frozenset({"logs"})
VOLATILE_FILES = frozenset({LOCK_NAME})
DB_PREFIX = "openfilm.sqlite"


def snapshot(data_dir: Path, *, include_db: bool = False) -> dict[str, str]:
    """Map of relative path -> SHA-256 for every file in the data directory."""
    result: dict[str, str] = {}
    for path in sorted(data_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(data_dir)
        if rel.parts[0] in VOLATILE_DIRS or rel.name in VOLATILE_FILES:
            continue
        if not include_db and len(rel.parts) == 1 and rel.name.startswith(DB_PREFIX):
            continue
        result[rel.as_posix()] = sha256_file(path)
    return result


def changed_files(before: dict[str, str], after: dict[str, str]) -> dict[str, list[str]]:
    """Files removed or modified between two snapshots (additions are reported too)."""
    return {
        "removed": sorted(set(before) - set(after)),
        "modified": sorted(k for k in before.keys() & after.keys() if before[k] != after[k]),
        "added": sorted(set(after) - set(before)),
    }
