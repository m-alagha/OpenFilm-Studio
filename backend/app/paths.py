"""User-data directory resolution.

User data always lives outside the application directory (git checkout, release
archive or container image), so updates and ``git clean`` can never touch it.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from pathlib import Path, PurePosixPath

APP_DIR_NAME_WINDOWS_MAC = "OpenFilmStudio"
APP_DIR_NAME_LINUX = "openfilm-studio"
DATA_DIR_ENV = "OPENFILM_DATA_DIR"
SUBDIRS = ("media", "backups", "logs")

# backend/app/paths.py -> repository / application root.
APP_ROOT = Path(__file__).resolve().parents[2]


class DataDirError(Exception):
    pass


def default_data_dir(
    platform: str | None = None,
    env: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> Path:
    """OS-conventional per-user data directory.

    Windows uses LOCALAPPDATA (not roaming APPDATA): generated media can be large
    and must not sync through roaming profiles.
    """
    platform = platform or sys.platform
    env = os.environ if env is None else env
    home = home or Path.home()

    if platform.startswith("win"):
        base = env.get("LOCALAPPDATA") or str(home / "AppData" / "Local")
        return Path(base) / APP_DIR_NAME_WINDOWS_MAC
    if platform == "darwin":
        return home / "Library" / "Application Support" / APP_DIR_NAME_WINDOWS_MAC
    xdg = env.get("XDG_DATA_HOME")
    # XDG requires an absolute path; judge it with POSIX rules on every host OS.
    base_path = Path(xdg) if xdg and PurePosixPath(xdg).is_absolute() else home / ".local" / "share"
    return base_path / APP_DIR_NAME_LINUX


def resolve_data_dir(env: Mapping[str, str] | None = None) -> Path:
    env = os.environ if env is None else env
    override = env.get(DATA_DIR_ENV, "").strip()
    if override:
        path = Path(override).expanduser()
        if not path.is_absolute():
            raise DataDirError(f"{DATA_DIR_ENV} must be an absolute path")
        return path
    return default_data_dir(env=env)


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def prepare_data_dir(path: Path, app_root: Path = APP_ROOT) -> Path:
    """Create the data directory layout, refusing locations inside the app."""
    resolved = path.resolve()
    if is_within(resolved, app_root):
        raise DataDirError(
            f"data directory {resolved} is inside the application directory {app_root}; "
            "user data must live outside the app so updates cannot touch it"
        )
    resolved.mkdir(parents=True, exist_ok=True)
    for name in SUBDIRS:
        (resolved / name).mkdir(exist_ok=True)
    return resolved
