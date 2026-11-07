"""Test-wide guards and fixtures.

No test may open a non-loopback network connection. Loopback is allowed so tests
can talk to a real local server process.
"""

from __future__ import annotations

import ipaddress
import json
import socket
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

_real_connect = socket.socket.connect
_real_connect_ex = socket.socket.connect_ex
_real_create_connection = socket.create_connection
ALLOW_NON_LOOPBACK: set[str] = set()


def _is_allowed(address: Any) -> bool:
    if isinstance(address, tuple) and address:
        host = str(address[0])
        if host == "localhost" or host in ALLOW_NON_LOOPBACK:
            return True
        try:
            return ipaddress.ip_address(host).is_loopback
        except ValueError:
            return False
    return False


@pytest.fixture(autouse=True)
def _block_network(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    def connect(self: socket.socket, address: Any) -> None:
        if not _is_allowed(address):
            raise AssertionError(f"network access attempted during tests: {address!r}")
        _real_connect(self, address)

    def connect_ex(self: socket.socket, address: Any) -> int:
        if not _is_allowed(address):
            raise AssertionError(f"network access attempted during tests: {address!r}")
        return _real_connect_ex(self, address)

    def create_connection(address: Any, *args: Any, **kwargs: Any) -> socket.socket:
        if not _is_allowed(address):
            raise AssertionError(f"network access attempted during tests: {address!r}")
        return _real_create_connection(address, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket.socket, "connect_ex", connect_ex)
    monkeypatch.setattr(socket, "create_connection", create_connection)
    yield


@pytest.fixture
def allow_non_loopback() -> Iterator[set[str]]:
    """Addresses a single test may probe (e.g. this machine's LAN IP)."""
    yield ALLOW_NON_LOOPBACK
    ALLOW_NON_LOOPBACK.clear()


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path / "openfilm-data")


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings), base_url="http://127.0.0.1:8765") as test_client:
        yield test_client


# --- update-manager helpers (all offline) -------------------------------------

REPO_URL = "https://github.com/m-alagha/OpenFilm-Studio"


def release_json(
    tag: str,
    *,
    draft: Any = False,
    prerelease: Any = False,
    body: Any = "Notes",
    assets: Any = None,
    **overrides: Any,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "tag_name": tag,
        "name": f"OpenFilm Studio {tag}",
        "body": body,
        "draft": draft,
        "prerelease": prerelease,
        "published_at": "2026-11-01T10:00:00Z",
        "html_url": f"{REPO_URL}/releases/tag/{tag}",
        "assets": [] if assets is None else assets,
    }
    data.update(overrides)
    return data


def asset_json(tag: str, name: str, size: Any = 1234, **overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "name": name,
        "size": size,
        "browser_download_url": f"{REPO_URL}/releases/download/{tag}/{name}",
        "digest": "sha256:" + "a" * 64,
    }
    data.update(overrides)
    return data


class FakeFetcher:
    """Records calls; returns a payload or raises the configured error."""

    def __init__(self, payload: object = None, error: Exception | None = None) -> None:
        self.payload: object = [] if payload is None else payload
        self.error = error
        self.calls = 0

    def __call__(self) -> bytes:
        self.calls += 1
        if self.error is not None:
            raise self.error
        if isinstance(self.payload, bytes):
            return self.payload
        return json.dumps(self.payload).encode()
