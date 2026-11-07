"""Anonymous, read-only fetch of public release metadata from GitHub.

Privacy: the request is a fixed GET to a fixed URL with three fixed headers. It
carries no cookies, credentials, identifiers, app data or query beyond paging.
Contract verified 2026-11-07 against docs.github.com (see docs/UPDATES.md).
"""

from __future__ import annotations

import socket
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from email.message import Message
from http.client import HTTPMessage
from typing import IO
from urllib.parse import urlsplit

from app.updates import REPOSITORY

API_HOST = "api.github.com"
RELEASES_URL = f"https://{API_HOST}/repos/{REPOSITORY}/releases?per_page=30"
API_VERSION = "2026-03-10"
USER_AGENT = "OpenFilm-Studio-Updater"
TIMEOUT_S = 10.0
MAX_RESPONSE_BYTES = 2_000_000
MAX_RETRY_AFTER_S = 24 * 3600

ReleaseFetcher = Callable[[], bytes]


class FetchError(Exception):
    """Normalized fetch failure. ``code`` is one of the CODE_* constants."""

    OFFLINE = "offline"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    HTTP_ERROR = "http_error"
    TOO_LARGE = "too_large"
    BAD_REDIRECT = "bad_redirect"

    def __init__(self, code: str, message: str, retry_after_s: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.retry_after_s = retry_after_s


def build_request() -> urllib.request.Request:
    return urllib.request.Request(  # noqa: S310 - fixed https URL
        RELEASES_URL,
        method="GET",
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": USER_AGENT,
        },
    )


class _SameHostRedirect(urllib.request.HTTPRedirectHandler):
    """Follow redirects only to https://api.github.com (e.g. a renamed repository)."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: HTTPMessage,
        newurl: str,
    ) -> urllib.request.Request | None:
        target = urlsplit(newurl)
        if target.scheme != "https" or target.hostname != API_HOST:
            raise FetchError(FetchError.BAD_REDIRECT, "redirect away from api.github.com refused")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _retry_after(headers: Message | None, now: float) -> int | None:
    if headers is None:
        return None
    value = headers.get("retry-after")
    if value and value.isdigit():
        return min(int(value), MAX_RETRY_AFTER_S)
    reset = headers.get("x-ratelimit-reset")
    if headers.get("x-ratelimit-remaining") == "0" and reset and reset.isdigit():
        return max(0, min(int(reset) - int(now), MAX_RETRY_AFTER_S))
    return None


def fetch_releases(
    opener: urllib.request.OpenerDirector | None = None, timeout: float = TIMEOUT_S
) -> bytes:
    opener = opener or urllib.request.build_opener(_SameHostRedirect())
    try:
        with opener.open(build_request(), timeout=timeout) as response:
            body: bytes = response.read(MAX_RESPONSE_BYTES + 1)
    except FetchError:
        raise
    except urllib.error.HTTPError as exc:
        retry = _retry_after(exc.headers, time.time())
        if exc.code == 429 or (exc.code == 403 and retry is not None):
            raise FetchError(FetchError.RATE_LIMITED, "GitHub rate limit reached", retry) from None
        raise FetchError(FetchError.HTTP_ERROR, f"GitHub returned HTTP {exc.code}") from None
    except TimeoutError:
        raise FetchError(FetchError.TIMEOUT, "GitHub did not respond in time") from None
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, TimeoutError | socket.timeout):
            raise FetchError(FetchError.TIMEOUT, "GitHub did not respond in time") from None
        raise FetchError(FetchError.OFFLINE, "could not reach GitHub") from None
    except OSError:
        raise FetchError(FetchError.OFFLINE, "could not reach GitHub") from None
    if len(body) > MAX_RESPONSE_BYTES:
        raise FetchError(FetchError.TOO_LARGE, "release list exceeds size limit")
    return body
