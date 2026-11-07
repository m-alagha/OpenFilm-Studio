#!/usr/bin/env python3
"""Fail if git-tracked (or about-to-be-tracked) files contain secrets.

Usage:
    python scripts/check_secrets.py            # scan the git working tree
    python scripts/check_secrets.py PATH...    # scan specific files
Exit code 0 = clean, 1 = findings. Matched values are never printed.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PATTERNS: dict[str, re.Pattern[str]] = {
    "google-api-key": re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----"),
    "service-account-json": re.compile(r"\"type\"\s*:\s*\"service_account\""),
    "api-key-assignment": re.compile(
        r"(?i)\b[A-Z0-9_]*API_KEY\s*=\s*[\"']?(?!your-|<|changeme|\$|\"|'|\s|$)[^\s\"'#]{8,}"
    ),
}
FORBIDDEN_NAMES = re.compile(r"(^|/)\.env(\.[^/]*)?$")
ALLOWED_ENV_NAMES = {".env.example"}


def git_files(root: Path) -> list[Path]:
    out = subprocess.run(  # noqa: S603
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],  # noqa: S607
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout
    return [root / p for p in out.decode().split("\0") if p]


def scan(paths: list[Path]) -> list[str]:
    findings: list[str] = []
    for path in paths:
        posix = path.as_posix()
        if FORBIDDEN_NAMES.search(posix) and path.name not in ALLOWED_ENV_NAMES:
            findings.append(f"{posix}: env file must not be committed")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for name, pattern in PATTERNS.items():
                if pattern.search(line):
                    findings.append(f"{posix}:{lineno}: possible {name}")
    return findings


def main(argv: list[str]) -> int:
    paths = [Path(a) for a in argv[1:]] or git_files(Path.cwd())
    findings = scan(paths)
    for finding in findings:
        print(finding)  # Location and rule name only; the matched value is never printed.
    print(f"secret scan: {len(paths)} files, {len(findings)} findings")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
