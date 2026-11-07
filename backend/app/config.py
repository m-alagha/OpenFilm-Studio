"""Runtime configuration from environment variables (no secrets live here)."""

from __future__ import annotations

import ipaddress
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from app.paths import resolve_data_dir

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
ALLOW_NON_LOOPBACK_ENV = "OPENFILM_ALLOW_NON_LOOPBACK"


class ConfigError(Exception):
    pass


def is_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host.strip("[]")).is_loopback
    except ValueError:
        return False


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    allow_non_loopback: bool = False

    @property
    def db_path(self) -> Path:
        return self.data_dir / "openfilm.sqlite"


def check_bind_host(host: str, allow_non_loopback: bool) -> None:
    if not is_loopback(host) and not allow_non_loopback:
        raise ConfigError(
            f"refusing to bind to non-loopback address {host!r}: OpenFilm Studio is "
            f"local-only. Set {ALLOW_NON_LOOPBACK_ENV}=1 only inside an isolated container."
        )


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    env = os.environ if env is None else env
    host = env.get("OPENFILM_HOST", DEFAULT_HOST).strip() or DEFAULT_HOST
    try:
        port = int(env.get("OPENFILM_PORT", str(DEFAULT_PORT)))
    except ValueError:
        raise ConfigError("OPENFILM_PORT must be an integer") from None
    if not 1 <= port <= 65535:
        raise ConfigError("OPENFILM_PORT must be between 1 and 65535")
    allow = env.get(ALLOW_NON_LOOPBACK_ENV, "") == "1"
    check_bind_host(host, allow)
    return Settings(data_dir=resolve_data_dir(env), host=host, port=port, allow_non_loopback=allow)
