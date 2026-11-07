"""Logging with mandatory credential redaction on every record."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.redaction import redact


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.getMessage())
        record.args = None
        if record.exc_info:
            # Render the traceback now so it is redacted too.
            text = logging.Formatter().formatException(record.exc_info)
            record.msg = f"{record.msg}\n{redact(text)}"
            record.exc_info = None
            record.exc_text = None
        return True


def configure_logging(logs_dir: Path | None, level: int = logging.INFO) -> None:
    """Attach redacting handlers to the root logger (console + local file)."""
    root = logging.getLogger()
    root.setLevel(level)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if logs_dir is not None:
        handlers.append(
            RotatingFileHandler(
                logs_dir / "openfilm.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
            )
        )
    for handler in list(root.handlers):
        if getattr(handler, "_openfilm", False):
            root.removeHandler(handler)
            handler.close()
    for handler in handlers:
        handler.setFormatter(formatter)
        handler.addFilter(RedactingFilter())
        handler._openfilm = True  # type: ignore[attr-defined]
        root.addHandler(handler)
