"""Run the backend: ``python -m app``. Binds to 127.0.0.1 unless explicitly overridden."""

from __future__ import annotations

import os
import sys

import uvicorn

from app.config import ConfigError, load_settings
from app.logging_setup import configure_logging
from app.main import create_app
from app.paths import DataDirError, prepare_data_dir


def main() -> int:
    # Defence in depth: FastAPI depends on opentelemetry-api (no-op without an SDK).
    os.environ.setdefault("OTEL_SDK_DISABLED", "true")
    try:
        settings = load_settings()
        data_dir = prepare_data_dir(settings.data_dir)
    except (ConfigError, DataDirError) as exc:
        print(f"OpenFilm Studio cannot start: {exc}", file=sys.stderr)
        return 2
    configure_logging(data_dir / "logs")
    if settings.allow_non_loopback:
        print("WARNING: non-loopback binding enabled; the API has no authentication.")
    uvicorn.run(
        create_app(settings),
        host=settings.host,
        port=settings.port,
        log_config=None,  # use our redacting root handlers
        server_header=False,
        proxy_headers=False,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
