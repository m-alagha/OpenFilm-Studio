"""Single-instance lock on the user-data directory.

Uses an OS advisory lock (msvcrt on Windows, flock on macOS/Linux) on
``<data_dir>/.openfilm.lock``. The OS releases it when the process exits or
crashes, so a stale lock file never blocks startup. The file is never deleted;
its contents (pid, start time) are informational only.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import IO

LOCK_NAME = ".openfilm.lock"


class DataDirLockedError(Exception):
    pass


def _try_lock(fh: IO[bytes]) -> bool:
    if sys.platform == "win32":
        import msvcrt

        fh.seek(0)
        try:
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            return False
        return True
    import fcntl

    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return False
    return True


def _unlock(fh: IO[bytes]) -> None:
    if sys.platform == "win32":
        import msvcrt

        fh.seek(0)
        msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


class DataDirLock:
    def __init__(self, data_dir: Path) -> None:
        self.path = data_dir / LOCK_NAME
        self._fh: IO[bytes] | None = None

    @property
    def held(self) -> bool:
        return self._fh is not None

    def acquire(self) -> DataDirLock:
        if self._fh is not None:
            return self
        fh = self.path.open("a+b")  # never truncate before holding the lock
        if not _try_lock(fh):
            fh.close()
            raise DataDirLockedError(
                f"OpenFilm Studio is already running with this data folder ({self.path.parent}). "
                "Close the other window first."
            )
        info = {"pid": os.getpid(), "started_at": datetime.now(UTC).isoformat()}
        fh.seek(0)
        fh.truncate()
        fh.write(json.dumps(info).encode())
        fh.flush()
        self._fh = fh
        return self

    def release(self) -> None:
        if self._fh is None:
            return
        try:
            _unlock(self._fh)
        finally:
            self._fh.close()
            self._fh = None

    def __enter__(self) -> DataDirLock:
        return self.acquire()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.release()
