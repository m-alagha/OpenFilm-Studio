"""Installation-type detection and installation-specific update guidance.

Commands are fixed templates. The only values inserted are a version that has
passed strict SemVer validation and this machine's own app path. Nothing from
release metadata (names, notes, URLs) is ever placed into a command.
"""

from __future__ import annotations

import enum
import os
import platform as platform_mod
import shlex
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePath

from app.updates import REPOSITORY
from app.updates.version import Version

INSTALL_TYPE_ENV = "OPENFILM_INSTALL_TYPE"
PACKAGED_MARKER = "openfilm-install.json"
OFFICIAL_REMOTE = f"https://github.com/{REPOSITORY}"

ONE_CLICK_REASON = (
    "Automatic installation is turned off until OpenFilm Studio publishes signed "
    "installers that this app can verify. Follow the steps below instead."
)


class InstallType(enum.StrEnum):
    GIT = "git"
    DOCKER = "docker"
    PACKAGED = "packaged"
    SOURCE = "source"


@dataclass(frozen=True)
class Step:
    title: str
    detail: str
    command: str | None = None


@dataclass(frozen=True)
class InstallInfo:
    type: InstallType
    os: str
    app_root: PurePath
    # Stays False until signed installers and a tested installer exist (D9).
    one_click_supported: bool = False
    one_click_reason: str = ONE_CLICK_REASON


def current_os(platform: str | None = None) -> str:
    platform = platform or sys.platform
    if platform.startswith("win"):
        return "windows"
    if platform == "darwin":
        return "macos"
    return "linux"


def current_arch(machine: str | None = None) -> str:
    machine = (machine or platform_mod.machine()).lower()
    return "arm64" if machine in {"arm64", "aarch64"} else "x64"


def detect_install_type(
    app_root: Path,
    env: Mapping[str, str] | None = None,
    dockerenv: Path = Path("/.dockerenv"),
) -> InstallType:
    env = os.environ if env is None else env
    override = env.get(INSTALL_TYPE_ENV, "").strip().lower()
    if override in {t.value for t in InstallType}:
        return InstallType(override)
    if dockerenv.exists():
        return InstallType.DOCKER
    if (app_root / ".git").exists():
        return InstallType.GIT
    if (app_root / PACKAGED_MARKER).is_file():
        return InstallType.PACKAGED
    return InstallType.SOURCE


def _cd(app_root: PurePath, os_name: str) -> str:
    if os_name == "windows":
        return f'cd /d "{app_root}"'
    return f"cd {shlex.quote(str(app_root))}"


def _start(os_name: str) -> str:
    return "scripts\\dev.cmd" if os_name == "windows" else "sh scripts/dev.sh"


def update_steps(info: InstallInfo, target: Version, release_url: str) -> list[Step]:
    tag = f"v{target}"
    data_note = "Your projects and media live in your data folder, which updates never touch."
    if info.type is InstallType.GIT:
        return [
            Step(
                "Stop OpenFilm Studio",
                "Press Ctrl+C in the window where OpenFilm Studio is running.",
            ),
            Step("Open a terminal in the OpenFilm Studio folder", "", _cd(info.app_root, info.os)),
            Step(
                "Check you're using the official repository",
                f"This should print {OFFICIAL_REMOTE} (optionally ending in .git).",
                "git remote get-url origin",
            ),
            Step(
                "Check for local changes",
                "If this prints anything, you have local changes. Back them up before continuing.",
                "git status --porcelain",
            ),
            Step("Download the new version", "", "git fetch --tags origin"),
            Step(f"Switch to version {target}", "", f"git checkout {tag}"),
            Step(
                "Start OpenFilm Studio",
                "Dependencies are reinstalled from the lockfiles, and your database is backed up "
                f"automatically before any upgrade. {data_note}",
                _start(info.os),
            ),
        ]
    if info.type is InstallType.DOCKER:
        return [
            Step(
                "Keep your data volume",
                "Your data lives in the volume mounted at OPENFILM_DATA_DIR. Never remove volumes "
                "when updating (do not use 'docker compose down -v').",
            ),
            Step("Stop the container", "", "docker compose down"),
            Step(
                f"Use the image for version {target}",
                f"Set the OpenFilm Studio image tag to {tag} in your compose file. Official image "
                f"details are listed on the release page: {release_url}",
            ),
            Step(
                "Pull and start the new version", "", "docker compose pull && docker compose up -d"
            ),
        ]
    if info.type is InstallType.PACKAGED:
        return [
            Step("Open the release page", release_url),
            Step(
                "Download the installer for your system",
                "Download only from the official release page above.",
            ),
            Step("Run the installer", f"Close OpenFilm Studio first. {data_note}"),
        ]
    return [
        Step("Open the release page", release_url),
        Step(
            "Download the source code",
            f"Download 'Source code (zip)' for {tag} and extract it into a new folder. "
            "Keep your current folder until the new one works.",
        ),
        Step(
            "Start the new version",
            f"In the new folder, run the start script. {data_note}",
            _start(info.os),
        ),
    ]


def rollback_steps(info: InstallInfo, current: Version) -> list[Step]:
    """How to get back to the previous version if an update goes wrong."""
    from_source = info.type in {InstallType.GIT, InstallType.SOURCE}
    restore = Step(
        "Restore your database if needed",
        "An older version can't open a database that a newer version upgraded. Close OpenFilm "
        "Studio, list the automatic backups taken before the upgrade, then restore one with "
        "'... python -m app.recovery restore <name>'. Restoring keeps a copy of the current "
        "database.",
        "uv run --project backend python -m app.recovery list" if from_source else None,
    )
    if info.type is InstallType.GIT:
        return [
            Step("Go back to your previous version", "", f"git checkout v{current}"),
            restore,
        ]
    return [
        Step(
            "Go back to your previous version", "Start OpenFilm Studio from your previous folder."
        ),
        restore,
    ]
