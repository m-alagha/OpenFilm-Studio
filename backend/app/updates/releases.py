"""Strict validation of GitHub "list releases" responses.

Release metadata is untrusted input. Anything malformed or pointing outside the
official repository is rejected rather than repaired. Field names follow the
GitHub REST API as verified on 2026-11-07 (docs/UPDATES.md).
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any

from app.updates import REPOSITORY
from app.updates.version import InvalidVersion, Version

MAX_RELEASES = 100
MAX_ASSETS = 50
MAX_NOTES_CHARS = 20_000
MAX_NAME_CHARS = 200
MAX_ASSET_BYTES = 8 * 1024**3
RELEASE_PAGE_PREFIX = f"https://github.com/{REPOSITORY}/releases/tag/"
DOWNLOAD_PREFIX = f"https://github.com/{REPOSITORY}/releases/download/"

_SAFE_ASSET_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,199}$")
_DIGEST = re.compile(r"^sha256:([0-9a-f]{64})$")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f​-‏‪-‮⁦-⁩]")


class InvalidReleaseData(ValueError):
    pass


@dataclass(frozen=True)
class ReleaseAsset:
    name: str
    size: int
    download_url: str
    sha256: str | None


@dataclass(frozen=True)
class Release:
    version: Version
    tag: str
    name: str
    notes: str
    published_at: str | None
    release_url: str
    assets: tuple[ReleaseAsset, ...]

    def to_json(self) -> str:
        data = asdict(self)
        data["version"] = str(self.version)
        return json.dumps(data, sort_keys=True)

    @classmethod
    def from_json(cls, text: str) -> Release:
        data = json.loads(text)
        return cls(
            version=Version.parse(data["version"]),
            tag=data["tag"],
            name=data["name"],
            notes=data["notes"],
            published_at=data["published_at"],
            release_url=data["release_url"],
            assets=tuple(ReleaseAsset(**a) for a in data["assets"]),
        )


def clean_text(value: str, limit: int) -> str:
    """Plain text only: strip control and bidi-override characters, cap length."""
    text = _CONTROL.sub("", value.replace("\r\n", "\n").replace("\r", "\n"))
    if len(text) > limit:
        text = text[:limit].rstrip() + "\n\n[Release notes truncated. See the release page.]"
    return text


def _same_url(actual: object, expected: str) -> bool:
    # GitHub may vary owner/repo letter case; nothing else may differ.
    return isinstance(actual, str) and actual.lower() == expected.lower() and actual.isascii()


def _asset(raw: Any, tag: str) -> ReleaseAsset:
    if not isinstance(raw, dict):
        raise InvalidReleaseData("asset is not an object")
    name, size = raw.get("name"), raw.get("size")
    if not isinstance(name, str) or not _SAFE_ASSET_NAME.fullmatch(name) or ".." in name:
        raise InvalidReleaseData("unsafe asset name")
    if type(size) is not int or not 0 <= size <= MAX_ASSET_BYTES:
        raise InvalidReleaseData("invalid asset size")
    url = raw.get("browser_download_url")
    expected = f"{DOWNLOAD_PREFIX}{tag}/{name}"
    if not _same_url(url, expected):
        raise InvalidReleaseData("asset URL outside the official repository")
    digest = raw.get("digest")
    match = _DIGEST.fullmatch(digest) if isinstance(digest, str) else None
    return ReleaseAsset(
        name=name, size=size, download_url=expected, sha256=match.group(1) if match else None
    )


def _release(raw: Any) -> Release | None:
    """Return a stable release, None to skip it (draft/prerelease), or raise."""
    if not isinstance(raw, dict):
        raise InvalidReleaseData("release is not an object")
    draft, prerelease = raw.get("draft"), raw.get("prerelease")
    if type(draft) is not bool or type(prerelease) is not bool:
        raise InvalidReleaseData("draft/prerelease flags must be booleans")
    if draft or prerelease:
        return None
    tag = raw.get("tag_name")
    try:
        version = Version.parse(tag)  # type: ignore[arg-type]
    except InvalidVersion as exc:
        raise InvalidReleaseData("tag is not a semantic version") from exc
    if not version.is_stable:
        return None
    assert isinstance(tag, str)  # noqa: S101 - narrowed by Version.parse
    release_url = f"{RELEASE_PAGE_PREFIX}{tag}"
    if not _same_url(raw.get("html_url"), release_url):
        raise InvalidReleaseData("release URL outside the official repository")
    assets_raw = raw.get("assets", [])
    if not isinstance(assets_raw, list) or len(assets_raw) > MAX_ASSETS:
        raise InvalidReleaseData("invalid assets list")
    name = raw.get("name")
    notes = raw.get("body")
    published = raw.get("published_at")
    return Release(
        version=version,
        tag=tag,
        name=clean_text(name, MAX_NAME_CHARS) if isinstance(name, str) and name.strip() else tag,
        notes=clean_text(notes, MAX_NOTES_CHARS) if isinstance(notes, str) else "",
        published_at=published if isinstance(published, str) and len(published) <= 40 else None,
        release_url=release_url,
        assets=tuple(_asset(a, tag) for a in assets_raw),
    )


def parse_releases(payload: bytes) -> tuple[list[Release], int]:
    """Parse a releases list. Returns (stable releases, number rejected as invalid)."""
    try:
        data = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidReleaseData("response is not valid JSON") from exc
    if not isinstance(data, list):
        raise InvalidReleaseData("expected a list of releases")
    releases: list[Release] = []
    rejected = 0
    for raw in data[:MAX_RELEASES]:
        try:
            release = _release(raw)
        except InvalidReleaseData:
            rejected += 1
            continue
        if release is not None:
            releases.append(release)
    return releases, rejected


def newest_update(releases: list[Release], current: Version) -> Release | None:
    """Highest stable release strictly newer than the running version (no downgrades)."""
    newer = [r for r in releases if r.version > current]
    return max(newer, key=lambda r: r.version) if newer else None
