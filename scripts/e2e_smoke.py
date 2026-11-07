#!/usr/bin/env python3
"""End-to-end smoke test of the real dev stack (backend + Vite UI), offline.

Checks: UI served, API reachable through the same-origin proxy, writes need the
client header, data persists across a backend restart, the UI degrades when the
backend is down, and no user data lands inside the repository.
Uses a temporary data directory and free ports; makes no external calls.
"""

from __future__ import annotations

import http.client
import json
import socket
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dev  # noqa: E402

ROOT = dev.ROOT
# Tooling caches and build output (not user data) are excluded from the snapshot.
SKIP_DIRS = {
    ".git", ".venv", "node_modules", "dist", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
}  # fmt: skip


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind((dev.HOST, 0))
        return int(sock.getsockname()[1])


def call(
    port: int, method: str, path: str, body: object = None, headers: dict[str, str] | None = None
) -> tuple[int, str]:
    conn = http.client.HTTPConnection(dev.HOST, port, timeout=10)
    try:
        payload = None if body is None else json.dumps(body)
        conn.request(method, path, body=payload, headers=headers or {})
        response = conn.getresponse()
        return response.status, response.read().decode("utf-8", "replace")
    finally:
        conn.close()


def check(condition: bool, label: str) -> None:
    print(f"  {'PASS' if condition else 'FAIL'}  {label}", flush=True)
    if not condition:
        raise SystemExit(1)


def repo_snapshot() -> set[str]:
    """Every file in the checkout, so any new file written by the app is detected."""
    files = set()
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT)
        if path.is_file() and not any(part in SKIP_DIRS for part in rel.parts):
            files.add(rel.as_posix())
    return files


def main() -> int:
    dev.ensure_dependencies()
    before = repo_snapshot()
    with tempfile.TemporaryDirectory(prefix="openfilm-e2e-") as tmp:
        data_dir = Path(tmp) / "data"
        ui = free_port()
        # Offline by design: update checks are switched off for the smoke test.
        env = {"OPENFILM_DATA_DIR": str(data_dir), "OPENFILM_UPDATE_CHECK": "0"}
        print(f"e2e: ui=:{ui} data={data_dir}")
        with dev.running(free_port(), ui, env) as servers:
            status, html = call(ui, "GET", "/")
            check(status == 200 and '<div id="root">' in html, "UI page served")
            status, body = call(ui, "GET", "/api/health")
            check(
                status == 200 and json.loads(body)["database"]["status"] == "ok",
                "API health via proxy",
            )

            write = {"Content-Type": "application/json", "Origin": f"http://{dev.HOST}:{ui}"}
            status, _ = call(
                ui, "PUT", "/api/settings/ui.welcome_dismissed", {"value": True}, write
            )
            check(status == 403, "write without client header rejected")
            status, body = call(
                ui,
                "PUT",
                "/api/settings/ui.welcome_dismissed",
                {"value": True},
                {**write, "X-OpenFilm-Client": "web"},
            )
            check(
                status == 200 and json.loads(body)["ui.welcome_dismissed"] is True, "setting saved"
            )

            status, body = call(ui, "GET", "/api/updates")
            updates = json.loads(body)
            check(
                status == 200
                and updates["disabled_by_environment"] is True
                and updates["install"]["one_click_supported"] is False,
                "update status served; checks off; one-click disabled",
            )
            status, body = call(
                ui, "POST", "/api/updates/install", None, {**write, "X-OpenFilm-Client": "web"}
            )
            check(
                status == 409 and json.loads(body)["error"]["code"] == "ONE_CLICK_UNSUPPORTED",
                "install request refused (nothing downloaded)",
            )

            servers.stop_backend()
            status, _ = call(ui, "GET", "/api/health")
            check(status >= 500, f"backend down is reported as an error (HTTP {status})")
            status, _ = call(ui, "GET", "/")
            check(status == 200, "UI still served while backend is down")

            servers.start_backend()
            status, body = call(ui, "GET", "/api/settings")
            check(
                status == 200 and json.loads(body)["ui.welcome_dismissed"] is True,
                "setting persisted across backend restart",
            )

        check(
            (data_dir / "openfilm.sqlite").is_file(), "database created in external data directory"
        )
        added = sorted(repo_snapshot() - before)
        check(not added, f"no files written inside the app/repository (new: {added or 'none'})")
    print("E2E SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
