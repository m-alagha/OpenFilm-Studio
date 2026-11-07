"""Redact credentials from text before it is logged or shown."""

from __future__ import annotations

import re

REDACTED = "[REDACTED]"

_VALUE = r"[^\s\"',}&]+"
_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # Google API keys anywhere in text.
    (re.compile(r"AIza[0-9A-Za-z_\-]{35}"), REDACTED),
    # key=... in URLs (some Google examples pass the key as a query parameter).
    (re.compile(rf"(?i)([?&]key=){_VALUE}"), rf"\1{REDACTED}"),
    # x-goog-api-key / authorization headers, plain or JSON-quoted.
    (re.compile(rf"(?i)(x-goog-api-key[\"']?\s*[:=]\s*[\"']?){_VALUE}"), rf"\1{REDACTED}"),
    (
        re.compile(rf"(?i)(authorization[\"']?\s*[:=]\s*[\"']?(?:bearer\s+)?){_VALUE}"),
        rf"\1{REDACTED}",
    ),
    # GEMINI_API_KEY=... / GOOGLE_API_KEY=... style assignments.
    (re.compile(rf"(?i)(_API_KEY\s*=\s*[\"']?){_VALUE}"), rf"\1{REDACTED}"),
)


def redact(text: str) -> str:
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text
