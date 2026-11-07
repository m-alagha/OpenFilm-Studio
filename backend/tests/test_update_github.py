"""GitHub fetch: privacy of the request and failure mapping (offline, mocked)."""

from __future__ import annotations

import io
import time
import urllib.error
import urllib.request
from email.message import Message
from http.client import HTTPMessage
from typing import Any

import pytest

from app.updates import github
from app.updates.github import FetchError, build_request, fetch_releases


def test_request_is_fixed_anonymous_and_minimal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "should-never-be-sent")
    monkeypatch.setenv("OPENFILM_DATA_DIR", "C:/Users/alex/secret-projects")
    req = build_request()
    assert (
        req.full_url == "https://api.github.com/repos/m-alagha/OpenFilm-Studio/releases?per_page=30"
    )
    assert req.get_method() == "GET"
    assert req.data is None
    assert {k.lower(): v for k, v in req.header_items()} == {
        "accept": "application/vnd.github+json",
        "x-github-api-version": "2026-03-10",
        "user-agent": "OpenFilm-Studio-Updater",
    }
    sent = repr(req.header_items()) + req.full_url
    for secret in ("should-never-be-sent", "secret-projects", "alex", "Authorization", "Cookie"):
        assert secret not in sent


class FakeResponse(io.BytesIO):
    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


class FakeOpener:
    def __init__(self, result: bytes | Exception) -> None:
        self.result = result
        self.requests: list[urllib.request.Request] = []

    def open(self, req: urllib.request.Request, timeout: float) -> FakeResponse:
        self.requests.append(req)
        assert timeout <= github.TIMEOUT_S
        if isinstance(self.result, Exception):
            raise self.result
        return FakeResponse(self.result)


def fetch(result: bytes | Exception) -> bytes:
    return fetch_releases(FakeOpener(result))  # type: ignore[arg-type]


def http_error(code: int, headers: dict[str, str] | None = None) -> urllib.error.HTTPError:
    msg = Message()
    for k, v in (headers or {}).items():
        msg[k] = v
    return urllib.error.HTTPError(github.RELEASES_URL, code, "error", msg, None)


def test_success_returns_body() -> None:
    assert fetch(b"[]") == b"[]"


def test_oversized_response_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(github, "MAX_RESPONSE_BYTES", 10)
    with pytest.raises(FetchError) as info:
        fetch(b"x" * 11)
    assert info.value.code == FetchError.TOO_LARGE


@pytest.mark.parametrize(
    ("error", "code", "retry"),
    [
        (http_error(429, {"retry-after": "120"}), FetchError.RATE_LIMITED, 120),
        (http_error(403, {"retry-after": "30"}), FetchError.RATE_LIMITED, 30),
        (http_error(429), FetchError.RATE_LIMITED, None),
        (http_error(403), FetchError.HTTP_ERROR, None),
        (http_error(404), FetchError.HTTP_ERROR, None),
        (http_error(500), FetchError.HTTP_ERROR, None),
        (urllib.error.URLError(OSError("Network is unreachable")), FetchError.OFFLINE, None),
        (urllib.error.URLError(TimeoutError()), FetchError.TIMEOUT, None),
        (TimeoutError(), FetchError.TIMEOUT, None),
        (ConnectionResetError(), FetchError.OFFLINE, None),
    ],
)
def test_failures_are_normalized(error: Exception, code: str, retry: int | None) -> None:
    with pytest.raises(FetchError) as info:
        fetch(error)
    assert info.value.code == code
    assert info.value.retry_after_s == retry


def test_primary_rate_limit_uses_reset_header() -> None:
    reset = str(int(time.time()) + 600)
    with pytest.raises(FetchError) as info:
        fetch(http_error(403, {"x-ratelimit-remaining": "0", "x-ratelimit-reset": reset}))
    assert info.value.code == FetchError.RATE_LIMITED
    assert info.value.retry_after_s is not None and 590 <= info.value.retry_after_s <= 600


def test_huge_retry_after_is_capped() -> None:
    with pytest.raises(FetchError) as info:
        fetch(http_error(429, {"retry-after": str(10**9)}))
    assert info.value.retry_after_s == github.MAX_RETRY_AFTER_S


@pytest.mark.parametrize(
    "target",
    [
        "https://evil.example/repos/x/releases",
        "http://api.github.com/repos/m-alagha/OpenFilm-Studio/releases",
        "https://api.github.com.evil.example/releases",
        "file:///etc/passwd",
    ],
)
def test_redirect_off_api_github_is_refused(target: str) -> None:
    handler = github._SameHostRedirect()
    with pytest.raises(FetchError) as info:
        handler.redirect_request(build_request(), io.BytesIO(), 301, "Moved", HTTPMessage(), target)
    assert info.value.code == FetchError.BAD_REDIRECT


def test_redirect_within_api_github_is_followed() -> None:
    handler = github._SameHostRedirect()
    target = "https://api.github.com/repositories/123/releases?per_page=30"
    new: Any = handler.redirect_request(
        build_request(), io.BytesIO(), 301, "Moved", HTTPMessage(), target
    )
    assert new is not None and new.full_url == target
