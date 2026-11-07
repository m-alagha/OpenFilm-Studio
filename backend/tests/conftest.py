"""Test-wide guards and fixtures.

No test may open a non-loopback network connection. Loopback is allowed so tests
can talk to a real local server process.
"""

from __future__ import annotations

import ipaddress
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
