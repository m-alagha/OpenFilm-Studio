from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient

from app import __version__
from app.config import Settings
from app.db.backup import sha256_file
from app.db.migrate import SCHEMA_VERSION
from app.main import create_app
from app.security import SECURITY_HEADERS

WRITE_HEADERS = {"X-OpenFilm-Client": "web"}


def test_health_ok(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app_version": __version__,
        "database": {"status": "ok", "code": None, "message": None},
    }


def test_security_headers_on_every_response(client: TestClient) -> None:
    for path in ("/api/health", "/api/does-not-exist"):
        response = client.get(path)
        for name, value in SECURITY_HEADERS.items():
            assert response.headers[name] == value
        assert "server" not in response.headers


def test_system_info(client: TestClient, settings: Settings) -> None:
    body = client.get("/api/system").json()
    assert body["app_version"] == __version__
    assert body["schema_version"] == SCHEMA_VERSION
    assert body["supported_schema_version"] == SCHEMA_VERSION
    assert body["data_dir"] == str(settings.data_dir)
    assert body["local_only"] is True
    assert body["provider"] == {"provider_id": "mock", "model_id": "mock-video-v0", "is_mock": True}


def test_settings_roundtrip(client: TestClient) -> None:
    assert client.get("/api/settings").json() == {"ui.welcome_dismissed": False}
    response = client.put(
        "/api/settings/ui.welcome_dismissed", json={"value": True}, headers=WRITE_HEADERS
    )
    assert response.status_code == 200
    assert response.json() == {"ui.welcome_dismissed": True}
    assert client.get("/api/settings").json() == {"ui.welcome_dismissed": True}


@pytest.mark.parametrize("value", [1, "true", None, [True]])
def test_settings_reject_wrong_type(client: TestClient, value: object) -> None:
    response = client.put(
        "/api/settings/ui.welcome_dismissed", json={"value": value}, headers=WRITE_HEADERS
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_SETTING"


def test_settings_reject_unknown_key(client: TestClient) -> None:
    response = client.put("/api/settings/api_key", json={"value": "x"}, headers=WRITE_HEADERS)
    assert response.status_code == 404


def test_write_without_client_header_is_forbidden(client: TestClient) -> None:
    response = client.put("/api/settings/ui.welcome_dismissed", json={"value": True})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "MISSING_CLIENT_HEADER"
    assert client.get("/api/settings").json() == {"ui.welcome_dismissed": False}


@pytest.mark.parametrize("origin", ["https://evil.example", "http://192.168.1.5:5173", "null"])
def test_cross_site_origin_is_forbidden(client: TestClient, origin: str) -> None:
    headers = {**WRITE_HEADERS, "Origin": origin}
    response = client.put(
        "/api/settings/ui.welcome_dismissed", json={"value": True}, headers=headers
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "BAD_ORIGIN"
    assert client.get("/api/health", headers={"Origin": origin}).status_code == 403


@pytest.mark.parametrize("origin", ["http://127.0.0.1:5173", "http://localhost:5173"])
def test_local_origin_is_allowed(client: TestClient, origin: str) -> None:
    headers = {**WRITE_HEADERS, "Origin": origin}
    response = client.put(
        "/api/settings/ui.welcome_dismissed", json={"value": True}, headers=headers
    )
    assert response.status_code == 200


@pytest.mark.parametrize("host", ["evil.example", "evil.example:8765", "192.168.1.5:8765"])
def test_dns_rebinding_host_is_rejected(client: TestClient, host: str) -> None:
    response = client.get("/api/health", headers={"Host": host})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BAD_HOST"


@pytest.mark.parametrize("host", ["127.0.0.1:8765", "localhost:8765", "[::1]:8765"])
def test_loopback_host_is_accepted(client: TestClient, host: str) -> None:
    assert client.get("/api/health", headers={"Host": host}).status_code == 200


def test_no_cors_headers(client: TestClient) -> None:
    response = client.options(
        "/api/settings/ui.welcome_dismissed",
        headers={"Origin": "http://127.0.0.1:5173", "Access-Control-Request-Method": "PUT"},
    )
    assert "access-control-allow-origin" not in response.headers


def test_incompatible_database_blocks_api_and_is_untouched(settings: Settings) -> None:
    with TestClient(create_app(settings), base_url="http://127.0.0.1"):
        pass
    conn = sqlite3.connect(settings.db_path)
    conn.execute("UPDATE alembic_version SET version_num = 'future'")
    conn.commit()
    conn.close()
    before = sha256_file(settings.db_path)

    with TestClient(create_app(settings), base_url="http://127.0.0.1") as blocked:
        health = blocked.get("/api/health")
        assert health.status_code == 503
        assert health.json()["database"]["code"] == "DB_NEWER_SCHEMA"
        assert "newer version" in health.json()["database"]["message"]
        for path in ("/api/system", "/api/settings"):
            response = blocked.get(path)
            assert response.status_code == 503
            assert response.json()["error"]["code"] == "DB_NEWER_SCHEMA"
        write = blocked.put(
            "/api/settings/ui.welcome_dismissed", json={"value": True}, headers=WRITE_HEADERS
        )
        assert write.status_code == 503

    assert sha256_file(settings.db_path) == before


def test_persistence_across_restarts(settings: Settings) -> None:
    with TestClient(create_app(settings), base_url="http://127.0.0.1") as first:
        first.put("/api/settings/ui.welcome_dismissed", json={"value": True}, headers=WRITE_HEADERS)
    with TestClient(create_app(settings), base_url="http://127.0.0.1") as second:
        assert second.get("/api/settings").json() == {"ui.welcome_dismissed": True}
        assert second.get("/api/system").json()["schema_version"] == SCHEMA_VERSION
