from __future__ import annotations

import importlib.util
import logging
from pathlib import Path

import pytest

from app.logging_setup import configure_logging
from app.redaction import REDACTED

FAKE_KEY = "AIza" + "Z" * 35


def test_log_records_are_redacted_in_file_and_console(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    configure_logging(tmp_path)
    log = logging.getLogger("openfilm.test")
    try:
        log.error("provider rejected key %s via ?key=%s", FAKE_KEY, "secret123")
        try:
            raise ValueError(f"boom x-goog-api-key: {FAKE_KEY}")
        except ValueError:
            log.exception("failure")
    finally:
        root = logging.getLogger()
        for handler in [h for h in root.handlers if getattr(h, "_openfilm", False)]:
            root.removeHandler(handler)
            handler.close()

    file_text = (tmp_path / "openfilm.log").read_text(encoding="utf-8")
    console_text = capsys.readouterr().err
    for text in (file_text, console_text):
        assert FAKE_KEY not in text
        assert "secret123" not in text
        assert REDACTED in text
        assert "ValueError" in text


def test_no_opentelemetry_sdk_or_exporter_installed() -> None:
    # FastAPI depends on opentelemetry-api, which is a no-op without an SDK.
    # An SDK or exporter could transmit data, so it must never be installed.
    for module in ("opentelemetry.sdk", "opentelemetry.exporter"):
        try:
            spec = importlib.util.find_spec(module)
        except ModuleNotFoundError:
            spec = None
        assert spec is None, f"{module} must not be installed (no telemetry)"
