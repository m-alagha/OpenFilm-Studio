#!/usr/bin/env python3
"""Start OpenFilm Studio for local development with one command.

    scripts/dev.sh            (macOS / Linux)
    scripts\\dev.cmd           (Windows: cmd or PowerShell)
    python scripts/dev.py     (any OS, Python >= 3.11)

Installs missing dependencies, starts the backend and the UI on 127.0.0.1 only,
waits until both respond, then opens your browser. Ctrl+C stops everything.
Standard library only.
"""

from __future__ import annotations

import argparse
import http.client
import os
import shutil
import socket
import subprocess
import sys
import time
import webbrowser
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
HOST = "127.0.0.1"
IS_WINDOWS = os.name == "nt"


class DevError(Exception):
    pass


def say(message: str) -> None:
    print(f"[openfilm] {message}", flush=True)


def venv_python() -> Path:
    sub = ("Scripts", "python.exe") if IS_WINDOWS else ("bin", "python")
    return BACKEND.joinpath(".venv", *sub)


def require_tool(name: str, hint: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise DevError(f"{name} was not found. {hint}")
    return path


def ensure_dependencies() -> None:
    if not venv_python().exists():
        uv = require_tool(
            "uv", "Install uv: https://docs.astral.sh/uv/getting-started/installation/"
        )
        say("installing backend dependencies (first run)...")
        subprocess.run([uv, "sync", "--frozen", "--extra", "dev"], cwd=BACKEND, check=True)  # noqa: S603
    if not (FRONTEND / "node_modules" / "vite").exists():
        npm = require_tool(
            "npm.cmd" if IS_WINDOWS else "npm", "Install Node.js 22+: https://nodejs.org"
        )
        say("installing frontend dependencies (first run)...")
        subprocess.run([npm, "ci"], cwd=FRONTEND, check=True)  # noqa: S603


def check_port_free(port: int, what: str, env_var: str) -> None:
    with socket.socket() as sock:
        try:
            sock.bind((HOST, port))
        except OSError:
            raise DevError(
                f"port {port} ({what}) is already in use. Is OpenFilm Studio already running? "
                f"Close it, or choose another port with {env_var}=<port>."
            ) from None


def http_status(port: int, path: str) -> int | None:
    conn = http.client.HTTPConnection(HOST, port, timeout=2)
    try:
        conn.request("GET", path)
        return conn.getresponse().status
    except OSError:
        return None
    finally:
        conn.close()


def wait_for(port: int, path: str, ok: set[int], proc: subprocess.Popen[bytes], what: str) -> None:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if http_status(port, path) in ok:
            return
        if proc.poll() is not None:
            raise DevError(
                f"{what} exited during startup (code {proc.returncode}); see output above"
            )
        time.sleep(0.3)
    raise DevError(f"{what} did not become ready within 60 seconds")


def stop(proc: subprocess.Popen[bytes] | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


@dataclass
class DevServers:
    backend_port: int
    ui_port: int
    env: dict[str, str] = field(default_factory=dict)
    backend: subprocess.Popen[bytes] | None = None
    ui: subprocess.Popen[bytes] | None = None

    @property
    def url(self) -> str:
        return f"http://{HOST}:{self.ui_port}/"

    def _env(self) -> dict[str, str]:
        return {
            **os.environ,
            **self.env,
            "OPENFILM_HOST": HOST,
            "OPENFILM_PORT": str(self.backend_port),
            "OPENFILM_UI_PORT": str(self.ui_port),
            "OTEL_SDK_DISABLED": "true",
        }

    def start_backend(self) -> None:
        check_port_free(self.backend_port, "backend", "OPENFILM_PORT")
        cmd = [str(venv_python()), "-m", "app"]
        self.backend = subprocess.Popen(cmd, cwd=BACKEND, env=self._env())  # noqa: S603
        # 503 = running but blocked by an incompatible database; the UI explains it.
        wait_for(self.backend_port, "/api/health", {200, 503}, self.backend, "backend")

    def start_ui(self) -> None:
        check_port_free(self.ui_port, "UI", "OPENFILM_UI_PORT")
        node = require_tool("node", "Install Node.js 22+: https://nodejs.org")
        vite = FRONTEND / "node_modules" / "vite" / "bin" / "vite.js"
        self.ui = subprocess.Popen([node, str(vite)], cwd=FRONTEND, env=self._env())  # noqa: S603
        wait_for(self.ui_port, "/", {200}, self.ui, "UI dev server")

    def stop_backend(self) -> None:
        stop(self.backend)
        self.backend = None

    def stop_all(self) -> None:
        stop(self.ui)
        self.ui = None
        self.stop_backend()


@contextmanager
def running(
    backend_port: int, ui_port: int, env: Mapping[str, str] | None = None
) -> Iterator[DevServers]:
    servers = DevServers(backend_port, ui_port, dict(env or {}))
    try:
        servers.start_backend()
        servers.start_ui()
        yield servers
    finally:
        servers.stop_all()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Start OpenFilm Studio (development).")
    parser.add_argument("--no-browser", action="store_true", help="don't open a browser")
    parser.add_argument(
        "--smoke", action="store_true", help="start, verify UI and API through the proxy, then stop"
    )
    args = parser.parse_args(argv)

    backend_port = int(os.environ.get("OPENFILM_PORT", "8765"))
    ui_port = int(os.environ.get("OPENFILM_UI_PORT", "5173"))
    try:
        ensure_dependencies()
        with running(backend_port, ui_port) as servers:
            if args.smoke:
                for path in ("/", "/api/health"):
                    status = http_status(ui_port, path)
                    if status != 200:
                        raise DevError(f"smoke check failed: GET {path} -> {status}")
                say("smoke check passed: UI and API reachable through the local proxy")
                return 0
            say(f"OpenFilm Studio is running at {servers.url}  (Ctrl+C to stop)")
            if not args.no_browser:
                webbrowser.open(servers.url)
            while True:
                for proc, name in ((servers.backend, "backend"), (servers.ui, "UI")):
                    if proc is not None and proc.poll() is not None:
                        raise DevError(f"{name} stopped unexpectedly (code {proc.returncode})")
                time.sleep(0.5)
    except KeyboardInterrupt:
        say("stopping...")
        return 0
    except (DevError, subprocess.CalledProcessError) as exc:
        say(f"error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
