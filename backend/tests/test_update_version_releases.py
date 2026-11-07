from __future__ import annotations

import json

import pytest
from conftest import REPO_URL, asset_json, release_json

from app.updates.releases import (
    MAX_NOTES_CHARS,
    InvalidReleaseData,
    newest_update,
    parse_releases,
)
from app.updates.version import InvalidVersion, Version

OTHER_TAG_URL = f"{REPO_URL}/releases/download/v1.0.0/app.zip"
PLAIN_HTTP_URL = REPO_URL.replace("https:", "http:") + "/releases/download/v2.0.0/app.zip"

# --- SemVer ---------------------------------------------------------------------


def test_semver_precedence_matches_spec_example() -> None:
    # Example ordering from semver.org §11.
    ordered = [
        "1.0.0-alpha",
        "1.0.0-alpha.1",
        "1.0.0-alpha.beta",
        "1.0.0-beta",
        "1.0.0-beta.2",
        "1.0.0-beta.11",
        "1.0.0-rc.1",
        "1.0.0",
        "2.0.0",
        "2.1.0",
        "2.1.1",
    ]
    versions = [Version.parse(v) for v in ordered]
    assert versions == sorted(reversed(versions))
    for low, high in zip(versions, versions[1:], strict=False):
        assert low < high


def test_numeric_components_compare_numerically() -> None:
    assert Version.parse("1.10.0") > Version.parse("1.9.0")
    assert Version.parse("0.1.10") > Version.parse("0.1.9")


def test_build_metadata_is_ignored_and_v_prefix_allowed() -> None:
    assert Version.parse("v1.2.3+build.5") == Version.parse("1.2.3")
    assert str(Version.parse("v1.2.3-rc.1+b")) == "1.2.3-rc.1+b"
    assert Version.parse("1.2.3").is_stable
    assert not Version.parse("1.2.3-rc.1").is_stable


@pytest.mark.parametrize(
    "text",
    ["1.2", "1.2.3.4", "01.2.3", "1.02.3", "1.2.3-", "1.2.3-01", "V1.2.3", "latest", "", " 1.2.3",
     "1.2.3; rm -rf /", "1.2.3\n", "9" * 70 + ".0.0"],
)  # fmt: skip
def test_invalid_versions_rejected(text: str) -> None:
    with pytest.raises(InvalidVersion):
        Version.parse(text)


# --- release parsing --------------------------------------------------------------


def parse(*releases: object) -> tuple[list[str], int]:
    found, rejected = parse_releases(json.dumps(list(releases)).encode())
    return [str(r.version) for r in found], rejected


def test_only_published_stable_releases_are_kept() -> None:
    versions, rejected = parse(
        release_json("v1.0.0"),
        release_json("v1.1.0", draft=True),
        release_json("v1.2.0", prerelease=True),
        release_json("v1.3.0-rc.1"),  # pre-release tag without the flag
    )
    assert versions == ["1.0.0"]
    assert rejected == 0


@pytest.mark.parametrize(
    "bad",
    [
        release_json("v2.0.0", html_url="https://evil.example/releases/tag/v2.0.0"),
        release_json("v2.0.0", html_url="https://github.com/attacker/OpenFilm-Studio/releases/tag/v2.0.0"),
        release_json("v2.0.0", html_url="javascript:alert(1)"),
        release_json("v2.0.0", html_url=f"{REPO_URL}/releases/tag/v9.9.9"),
        release_json("v2.0.0", draft="false"),
        release_json("v2.0.0", prerelease=None),
        release_json("not-a-version"),
        release_json("v2.0.0", assets=[asset_json("v2.0.0", "../../evil.exe")]),
        release_json("v2.0.0", assets=[asset_json("v2.0.0", "dir/evil.zip")]),
        release_json("v2.0.0", assets=[asset_json("v2.0.0", "evil.zip\n")]),
        release_json("v2.0.0", assets=[asset_json("v2.0.0", "evil.zip", size=-1)]),
        release_json("v2.0.0", assets=[asset_json("v2.0.0", "evil.zip", size="12")]),
        release_json("v2.0.0", assets=[asset_json("v2.0.0", "evil.zip", size=10**12)]),
        release_json("v2.0.0", assets=[asset_json(
            "v2.0.0", "app.zip", browser_download_url="https://evil.example/app.zip")]),
        release_json("v2.0.0", assets=[asset_json(
            "v2.0.0", "app.zip", browser_download_url=OTHER_TAG_URL)]),
        release_json("v2.0.0", assets=[asset_json(
            "v2.0.0", "app.zip", browser_download_url=PLAIN_HTTP_URL)]),
        release_json("v2.0.0", assets="nope"),
        "a string, not an object",
    ],
)  # fmt: skip
def test_malicious_or_malformed_releases_are_rejected(bad: object) -> None:
    versions, rejected = parse(bad, release_json("v1.0.0"))
    assert versions == ["1.0.0"]
    assert rejected == 1


def test_owner_case_difference_is_accepted() -> None:
    versions, _ = parse(
        release_json(
            "v1.0.0", html_url="https://github.com/M-Alagha/openfilm-studio/releases/tag/v1.0.0"
        )
    )
    assert versions == ["1.0.0"]


@pytest.mark.parametrize("payload", [b"not json", b'{"releases": []}', b"\xff\xfe", b"null"])
def test_invalid_response_shapes_raise(payload: bytes) -> None:
    with pytest.raises(InvalidReleaseData):
        parse_releases(payload)


def test_release_notes_are_plain_text_and_capped() -> None:
    body = "Fixes\r\n- one\x00\x07 ‮evil‬\n" + "x" * (MAX_NOTES_CHARS + 50)
    (release,), _ = parse_releases(json.dumps([release_json("v1.0.0", body=body)]).encode())
    assert "\x00" not in release.notes and "\x07" not in release.notes
    assert "‮" not in release.notes and "\r" not in release.notes
    assert release.notes.startswith("Fixes\n- one evil\n")
    assert release.notes.endswith("[Release notes truncated. See the release page.]")


def test_digest_accepted_only_in_strict_form() -> None:
    assets = [
        asset_json("v1.0.0", "a.zip"),
        asset_json("v1.0.0", "b.zip", digest="md5:abc"),
        asset_json("v1.0.0", "c.zip", digest=None),
    ]
    (release,), _ = parse_releases(json.dumps([release_json("v1.0.0", assets=assets)]).encode())
    assert [a.sha256 for a in release.assets] == ["a" * 64, None, None]


def test_newest_update_picks_highest_newer_and_never_downgrades() -> None:
    releases, _ = parse_releases(
        json.dumps([release_json(t) for t in ("v0.9.0", "v1.2.0", "v1.10.0", "v1.1.0")]).encode()
    )
    update = newest_update(releases, Version.parse("1.1.0"))
    assert update is not None and str(update.version) == "1.10.0"
    assert newest_update(releases, Version.parse("1.10.0")) is None  # equal: not offered
    assert newest_update(releases, Version.parse("2.0.0")) is None  # older: never offered


def test_release_roundtrips_through_cache_json() -> None:
    (release,), _ = parse_releases(
        json.dumps([release_json("v1.0.0", assets=[asset_json("v1.0.0", "a.zip")])]).encode()
    )
    from app.updates.releases import Release

    assert Release.from_json(release.to_json()) == release
