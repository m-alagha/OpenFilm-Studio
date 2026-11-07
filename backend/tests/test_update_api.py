"""Update API, background checks and non-blocking startup (offline)."""

from __future__ import annotations

import dataclasses
import sqlite3
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from conftest import FakeFetcher, release_json
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.updates.github import FetchError
from app.updates.install import InstallInfo, InstallType

WRITE = {"X-OpenFilm-Client": "web"}
BASE = "http://127.0.0.1:8765"


def make_client(settings: Settings, fetcher: FakeFetcher | object, **kwargs: object) -> TestClient:
    install = InstallInfo(InstallType.GIT, "windows", Path(r"C:\apps\OpenFilm-Studio"))
    app = create_app(settings, release_fetcher=fetcher, install=install, **kwargs)  # type: ignore[arg-type]
    return TestClient(app, base_url=BASE)


@pytest.fixture
def fetcher() -> FakeFetcher:
    return FakeFetcher([release_json("v0.2.0", body="New timeline tools.")])


@pytest.fixture
def api(settings: Settings, fetcher: FakeFetcher) -> Iterator[TestClient]:
    with make_client(settings, fetcher) as client:
        yield client


def test_initial_status(api: TestClient, fetcher: FakeFetcher) -> None:
    body = api.get("/api/updates").json()
    assert body["current_version"] == "0.1.0"
    assert body["auto_check_enabled"] is True
    assert body["disclosure_acknowledged"] is False
    assert body["last_check_status"] == "never"
    assert body["available"] is None and body["notify"] is False
    assert body["install"]["type"] == "git" and body["install"]["one_click_supported"] is False
    assert fetcher.calls == 0


def test_manual_check_and_notification(api: TestClient) -> None:
    body = api.post("/api/updates/check", headers=WRITE).json()
    assert body["notify"] is True
    available = body["available"]
    assert available["version"] == "0.2.0"
    assert available["notes"] == "New timeline tools."
    assert available["release_url"].startswith("https://github.com/m-alagha/OpenFilm-Studio/")
    commands = [s["command"] for s in body["install"]["steps"] if s["command"]]
    assert "git checkout v0.2.0" in commands
    assert body["install"]["rollback_steps"]


def test_writes_require_client_header(api: TestClient, fetcher: FakeFetcher) -> None:
    for path in ("/api/updates/check", "/api/updates/snooze", "/api/updates/install"):
        assert api.post(path).status_code == 403
    assert (
        api.put("/api/updates/preferences", json={"auto_check_enabled": False}).status_code == 403
    )
    assert fetcher.calls == 0


def test_skip_and_snooze_via_api(api: TestClient) -> None:
    api.post("/api/updates/check", headers=WRITE)
    snoozed = api.post("/api/updates/snooze", headers=WRITE).json()
    assert snoozed["notify"] is False and snoozed["available"]["snoozed_until"]
    skipped = api.post("/api/updates/skip", json={"version": "0.2.0"}, headers=WRITE).json()
    assert skipped["available"]["skipped"] is True and skipped["notify"] is False
    bad = api.post("/api/updates/skip", json={"version": "1.0.0"}, headers=WRITE)
    assert bad.status_code == 409 and bad.json()["error"]["code"] == "NOT_OFFERED"


def test_install_is_refused_and_downloads_nothing(api: TestClient, fetcher: FakeFetcher) -> None:
    api.post("/api/updates/check", headers=WRITE)
    calls = fetcher.calls
    response = api.post("/api/updates/install", headers=WRITE)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ONE_CLICK_UNSUPPORTED"
    assert fetcher.calls == calls


@pytest.mark.parametrize("value", [1, "true", None])
def test_preferences_are_strictly_typed(api: TestClient, value: object) -> None:
    response = api.put(
        "/api/updates/preferences", json={"auto_check_enabled": value}, headers=WRITE
    )
    if value is None:
        assert response.status_code == 200  # null = leave unchanged
    else:
        assert response.status_code == 422


def test_preferences_persist_across_restart(settings: Settings, fetcher: FakeFetcher) -> None:
    with make_client(settings, fetcher) as first:
        first.put(
            "/api/updates/preferences",
            json={"auto_check_enabled": False, "disclosure_acknowledged": True},
            headers=WRITE,
        )
    with make_client(settings, fetcher) as second:
        body = second.get("/api/updates").json()
    assert body["auto_check_enabled"] is False and body["disclosure_acknowledged"] is True


def test_environment_switch_disables_checks(settings: Settings, fetcher: FakeFetcher) -> None:
    off = dataclasses.replace(settings, update_checks_disabled=True)
    with make_client(off, fetcher) as client:
        assert client.get("/api/updates").json()["disabled_by_environment"] is True
        response = client.post("/api/updates/check", headers=WRITE)
    assert response.status_code == 409 and response.json()["error"]["code"] == "UPDATES_DISABLED"
    assert fetcher.calls == 0


def _acknowledge(settings: Settings) -> None:
    with make_client(settings, FakeFetcher([])) as client:
        client.put(
            "/api/updates/preferences", json={"disclosure_acknowledged": True}, headers=WRITE
        )


def test_background_check_runs_after_disclosure(settings: Settings, fetcher: FakeFetcher) -> None:
    _acknowledge(settings)
    fast = dataclasses.replace(settings, update_initial_delay_s=0, update_poll_interval_s=0.05)
    with make_client(fast, fetcher) as client:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not client.get("/api/updates").json()["notify"]:
            time.sleep(0.05)
        assert client.get("/api/updates").json()["available"]["version"] == "0.2.0"
    assert fetcher.calls == 1  # 24h interval: no repeated requests


def test_startup_is_not_blocked_by_a_hanging_network(settings: Settings) -> None:
    _acknowledge(settings)
    release = threading.Event()

    def hanging() -> bytes:
        release.wait(10)
        raise FetchError(FetchError.TIMEOUT, "simulated hang")

    fast = dataclasses.replace(settings, update_initial_delay_s=0)
    started = time.monotonic()
    with make_client(fast, hanging) as client:
        assert client.get("/api/health").status_code == 200
        assert client.get("/api/settings").status_code == 200
        assert time.monotonic() - started < 3
        release.set()


def test_offline_background_failure_never_breaks_the_app(settings: Settings) -> None:
    _acknowledge(settings)
    offline = FakeFetcher(error=FetchError(FetchError.OFFLINE, "no network"))
    fast = dataclasses.replace(settings, update_initial_delay_s=0, update_poll_interval_s=0.05)
    with make_client(fast, offline) as client:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and offline.calls == 0:
            time.sleep(0.05)
        time.sleep(0.1)
        assert client.get("/api/health").status_code == 200
        assert client.get("/api/updates").json()["last_check_status"] == "offline"


def test_update_api_blocked_with_incompatible_database(
    settings: Settings, fetcher: FakeFetcher
) -> None:
    with make_client(settings, fetcher):
        pass
    conn = sqlite3.connect(settings.db_path)
    conn.execute("UPDATE alembic_version SET version_num = 'future'")
    conn.commit()
    conn.close()
    with make_client(settings, fetcher) as client:
        assert client.get("/api/updates").status_code == 503
        assert client.post("/api/updates/check", headers=WRITE).status_code == 503
    assert fetcher.calls == 0
