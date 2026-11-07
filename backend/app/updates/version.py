"""Semantic Versioning 2.0.0 parsing and precedence (https://semver.org)."""

from __future__ import annotations

import functools
import re
from dataclasses import dataclass

MAX_LENGTH = 64

# Official SemVer regex, with an optional leading "v" for git tags.
_SEMVER = re.compile(
    r"^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)


class InvalidVersion(ValueError):
    pass


@functools.total_ordering
@dataclass(frozen=True, eq=False)
class Version:
    major: int
    minor: int
    patch: int
    prerelease: tuple[str, ...] = ()
    build: str = ""

    @classmethod
    def parse(cls, text: str) -> Version:
        if not isinstance(text, str) or len(text) > MAX_LENGTH:
            raise InvalidVersion("not a version string")
        match = _SEMVER.fullmatch(text)
        if match is None:
            raise InvalidVersion(f"invalid semantic version: {text[:MAX_LENGTH]!r}")
        major, minor, patch, pre, build = match.groups()
        return cls(
            int(major), int(minor), int(patch), tuple(pre.split(".")) if pre else (), build or ""
        )

    @property
    def is_stable(self) -> bool:
        return not self.prerelease

    def _key(self) -> tuple[int, int, int, int, tuple[tuple[int, int | str], ...]]:
        # A pre-release has lower precedence than the associated normal version.
        # Numeric identifiers sort numerically and below alphanumeric ones.
        pre = tuple((0, int(p)) if p.isdigit() else (1, p) for p in self.prerelease)
        return (self.major, self.minor, self.patch, 0 if self.prerelease else 1, pre)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self._key() == other._key()  # build metadata is ignored

    def __lt__(self, other: Version) -> bool:
        return self._key() < other._key()

    def __hash__(self) -> int:
        return hash(self._key())

    def __str__(self) -> str:
        text = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            text += "-" + ".".join(self.prerelease)
        if self.build:
            text += "+" + self.build
        return text
