from __future__ import annotations

import pytest

from app.redaction import REDACTED, redact

# Built at runtime so this file never contains a key-shaped literal.
FAKE_KEY = "AIza" + "X" * 35


@pytest.mark.parametrize(
    "text",
    [
        f"error calling model: {FAKE_KEY}",
        "GET https://example.invalid/v1beta/interactions?alt=json&key=abc123secret",
        "x-goog-api-key: abc123secret",
        '{"x-goog-api-key": "abc123secret"}',
        "Authorization: Bearer abc123secret",
        "GEMINI_API_KEY" + "=abc123secret",
    ],
)
def test_secrets_are_redacted(text: str) -> None:
    out = redact(text)
    assert "abc123secret" not in out
    assert FAKE_KEY not in out
    assert REDACTED in out


def test_plain_text_is_untouched() -> None:
    text = "Shot 3: the keeper opens the door (16:9, 8s)."
    assert redact(text) == text
