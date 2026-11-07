"""Test-wide guards: no test may open a network connection."""

from __future__ import annotations

import socket
from collections.abc import Iterator
from typing import Any

import pytest


@pytest.fixture(autouse=True)
def _block_network(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    def guarded(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("network access attempted during tests")

    monkeypatch.setattr(socket.socket, "connect", guarded)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded)
    monkeypatch.setattr(socket, "create_connection", guarded)
    yield
