"""Real server process tests: loopback-only binding and restart persistence."""

from __future__ import annotations

import hashlib
import http.client
import json
import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def request(port: int, method: str, path: str, body: object = None) -> tuple[int, object]:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        headers = {"X-OpenFilm-Client": "web", "Content-Type": "application/json"}
        payload = None if body is None else json.dumps(body)
        conn.request(method, path, body=payload, headers=headers)
        response = conn.getresponse()
        return response.status, json.loads(response.read() or b"null")
    finally:
        conn.close()


@contextmanager
def server(data_dir: Path, port: int, **extra_env: str) -> Iterator[subprocess.Popen[bytes]]:
    env = {
        **os.environ,
        "OPENFILM_DATA_DIR": str(data_dir),
        "OPENFILM_PORT": str(port),
        "OPENFILM_UPDATE_CHECK": "0",
    }
    env.update(extra_env)
    proc = subprocess.Popen(
        [sys.executable, "-m", "app"],
        cwd=BACKEND_DIR,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 20
        while True:
            try:
                status, _ = request(port, "GET", "/api/health")
                if status == 200:
                    break
            except OSError:
                pass
            if proc.poll() is not None or time.monotonic() > deadline:
                raise AssertionError("backend did not start")
            time.sleep(0.2)
        yield proc
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def lan_addresses() -> list[str]:
    try:
        infos = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
    except OSError:
        return []
    return sorted({str(i[4][0]) for i in infos if not str(i[4][0]).startswith("127.")})


def test_binds_loopback_only_and_persists_across_restart(
    tmp_path: Path, allow_non_loopback: set[str]
) -> None:
    data_dir = tmp_path / "data"
    port = free_port()
    with server(data_dir, port):
        status, body = request(port, "PUT", "/api/settings/ui.welcome_dismissed", {"value": True})
        assert status == 200
        for address in lan_addresses():
            allow_non_loopback.add(address)
            try:
                with socket.socket() as sock:
                    sock.settimeout(2)
                    assert sock.connect_ex((address, port)) != 0, f"reachable on {address}"
            finally:
                allow_non_loopback.discard(address)

    with server(data_dir, port):
        status, body = request(port, "GET", "/api/settings")
        assert status == 200
        assert body == {"ui.welcome_dismissed": True}
    assert (data_dir / "openfilm.sqlite").exists()


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.10"])  # noqa: S104
def test_refuses_non_loopback_host(tmp_path: Path, host: str) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "app"],
        cwd=BACKEND_DIR,
        env={**os.environ, "OPENFILM_DATA_DIR": str(tmp_path), "OPENFILM_HOST": host},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 2
    assert "refusing to bind to non-loopback" in result.stderr


def test_refuses_data_dir_inside_repository() -> None:
    inside = BACKEND_DIR / "should-not-exist"
    result = subprocess.run(
        [sys.executable, "-m", "app"],
        cwd=BACKEND_DIR,
        env={**os.environ, "OPENFILM_DATA_DIR": str(inside)},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 2
    assert "inside the application directory" in result.stderr
    assert not inside.exists()


def test_second_instance_on_same_data_dir_is_refused(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    with server(data_dir, free_port()):
        db = data_dir / "openfilm.sqlite"
        before = hashlib.sha256(db.read_bytes()).hexdigest()
        result = subprocess.run(
            [sys.executable, "-m", "app"],
            cwd=BACKEND_DIR,
            env={**os.environ, "OPENFILM_DATA_DIR": str(data_dir),
                 "OPENFILM_PORT": str(free_port()), "OPENFILM_UPDATE_CHECK": "0"},
            capture_output=True,
            text=True,
            timeout=30,
        )  # fmt: skip
        assert result.returncode == 3
        assert "already running" in result.stderr
        assert hashlib.sha256(db.read_bytes()).hexdigest() == before
    # After the first instance stops (terminated, not cleanly closed), startup works again.
    with server(data_dir, free_port()):
        pass
