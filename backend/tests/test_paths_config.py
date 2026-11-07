from __future__ import annotations

from pathlib import Path

import pytest

from app.config import ConfigError, check_bind_host, is_loopback, load_settings
from app.paths import (
    APP_ROOT,
    DataDirError,
    default_data_dir,
    prepare_data_dir,
    resolve_data_dir,
)

HOME = Path("/home/alex")


@pytest.mark.parametrize(
    ("platform", "env", "expected"),
    [
        (
            "win32",
            {"LOCALAPPDATA": r"C:\Users\alex\AppData\Local"},
            Path(r"C:\Users\alex\AppData\Local") / "OpenFilmStudio",
        ),
        ("win32", {}, HOME / "AppData" / "Local" / "OpenFilmStudio"),
        ("darwin", {}, HOME / "Library" / "Application Support" / "OpenFilmStudio"),
        ("linux", {}, HOME / ".local" / "share" / "openfilm-studio"),
        ("linux", {"XDG_DATA_HOME": "/data/xdg"}, Path("/data/xdg") / "openfilm-studio"),
        (
            "linux",
            {"XDG_DATA_HOME": "relative/ignored"},
            HOME / ".local" / "share" / "openfilm-studio",
        ),
    ],
)
def test_default_data_dir_per_os(platform: str, env: dict[str, str], expected: Path) -> None:
    assert default_data_dir(platform=platform, env=env, home=HOME) == expected


def test_default_data_dir_is_outside_repository() -> None:
    assert not str(default_data_dir()).startswith(str(APP_ROOT))


def test_override_must_be_absolute(tmp_path: Path) -> None:
    assert resolve_data_dir({"OPENFILM_DATA_DIR": str(tmp_path)}) == tmp_path
    with pytest.raises(DataDirError):
        resolve_data_dir({"OPENFILM_DATA_DIR": "relative/data"})


def test_prepare_creates_layout(tmp_path: Path) -> None:
    root = prepare_data_dir(tmp_path / "d")
    assert {p.name for p in root.iterdir()} == {"media", "backups", "logs"}


@pytest.mark.parametrize("inside", [APP_ROOT / "data", APP_ROOT / "backend" / "x"])
def test_prepare_refuses_inside_app(inside: Path) -> None:
    with pytest.raises(DataDirError, match="inside the application directory"):
        prepare_data_dir(inside)
    assert not inside.exists()


@pytest.mark.parametrize("host", ["127.0.0.1", "127.0.0.2", "::1", "[::1]", "localhost"])
def test_loopback_hosts(host: str) -> None:
    assert is_loopback(host)
    check_bind_host(host, allow_non_loopback=False)


@pytest.mark.parametrize("host", ["0.0.0.0", "::", "192.168.1.10", "example.com"])  # noqa: S104
def test_non_loopback_refused_by_default(host: str) -> None:
    assert not is_loopback(host)
    with pytest.raises(ConfigError, match="non-loopback"):
        check_bind_host(host, allow_non_loopback=False)
    check_bind_host(host, allow_non_loopback=True)


def test_load_settings_defaults_to_loopback(tmp_path: Path) -> None:
    settings = load_settings({"OPENFILM_DATA_DIR": str(tmp_path)})
    assert settings.host == "127.0.0.1"
    assert settings.port == 8765
    assert not settings.allow_non_loopback


@pytest.mark.parametrize("port", ["abc", "0", "70000"])
def test_invalid_port(tmp_path: Path, port: str) -> None:
    with pytest.raises(ConfigError):
        load_settings({"OPENFILM_DATA_DIR": str(tmp_path), "OPENFILM_PORT": port})
