"""Local-only HTTP hardening for the backend.

Threat: a web page in the user's browser (any site) sending requests to
http://127.0.0.1:<port>. Defences:
- Host header must be a loopback name (blocks DNS-rebinding).
- Origin, when present, must be a loopback origin.
- State-changing requests need the custom header ``X-OpenFilm-Client``. Browsers
  cannot send it cross-origin without a CORS preflight, and this server enables
  no CORS at all, so other sites cannot forge writes.
- Strict security headers on every response.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from app.config import is_loopback

CLIENT_HEADER = "x-openfilm-client"
CLIENT_HEADER_VALUE = "web"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Cache-Control": "no-store",
}


def host_from_header(value: str) -> str:
    """Hostname from a Host header, handling ports and bracketed IPv6."""
    return urlsplit(f"//{value}").hostname or ""


def origin_is_local(origin: str) -> bool:
    parts = urlsplit(origin)
    return parts.scheme in {"http", "https"} and is_loopback(parts.hostname or "")


def _deny(status: int, code: str, message: str) -> Response:
    response = JSONResponse({"error": {"code": code, "message": message}}, status_code=status)
    response.headers.update(SECURITY_HEADERS)
    return response


async def local_only_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    if not is_loopback(host_from_header(request.headers.get("host", ""))):
        return _deny(400, "BAD_HOST", "requests must target localhost")
    origin = request.headers.get("origin")
    if origin is not None and not origin_is_local(origin):
        return _deny(403, "BAD_ORIGIN", "cross-site requests are not allowed")
    if (
        request.method not in SAFE_METHODS
        and request.headers.get(CLIENT_HEADER) != CLIENT_HEADER_VALUE
    ):
        return _deny(403, "MISSING_CLIENT_HEADER", "write requests must come from the app")
    response = await call_next(request)
    response.headers.update(SECURITY_HEADERS)
    return response
