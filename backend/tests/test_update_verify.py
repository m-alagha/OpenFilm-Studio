"""Release authenticity (Ed25519 manifest) and integrity (checksums, safe extraction)."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import stat
import tarfile
import zipfile
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from app.updates import verify
from app.updates.verify import (
    ManifestAsset,
    VerificationError,
    safe_extract,
    verify_artifact,
    verify_manifest,
)
from app.updates.version import Version

CURRENT = Version.parse("0.1.0")
TARGET = Version.parse("0.2.0")


@pytest.fixture(scope="module")
def keypair() -> tuple[Ed25519PrivateKey, dict[str, bytes]]:
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return private, {"test-key-1": public}


def manifest(**overrides: Any) -> bytes:
    doc: dict[str, Any] = {
        "schema": 1,
        "product": "openfilm-studio",
        "repository": "m-alagha/OpenFilm-Studio",
        "version": "0.2.0",
        "assets": [
            {"name": "OpenFilm-Studio-0.2.0-windows-x64.zip", "platform": "windows-x64",
             "sha256": "b" * 64, "size": 100},
        ],
    }  # fmt: skip
    doc.update(overrides)
    return json.dumps(doc).encode()


def sign(private: Ed25519PrivateKey, data: bytes, key_id: str = "test-key-1") -> bytes:
    return json.dumps(
        {"key_id": key_id, "signature": base64.b64encode(private.sign(data)).decode()}
    ).encode()


def check(data: bytes, sig: bytes, keys: dict[str, bytes], target: Version = TARGET) -> Any:
    return verify_manifest(
        data, sig, expected_version=target, current_version=CURRENT, trusted_keys=keys
    )


def code_of(fn: Any) -> str:
    with pytest.raises(VerificationError) as info:
        fn()
    return info.value.code


def test_valid_signed_manifest_is_accepted(
    keypair: tuple[Ed25519PrivateKey, dict[str, bytes]],
) -> None:
    private, keys = keypair
    data = manifest()
    result = check(data, sign(private, data), keys)
    assert result.version == TARGET
    asset = result.asset_for("windows-x64")
    assert asset is not None and asset.size == 100


def test_fails_closed_while_no_release_key_is_trusted(
    keypair: tuple[Ed25519PrivateKey, dict[str, bytes]],
) -> None:
    private, _ = keypair
    data = manifest()
    assert dict(verify.TRUSTED_RELEASE_KEYS) == {}  # no key ships until M11
    assert code_of(lambda: verify_manifest(
        data, sign(private, data), expected_version=TARGET, current_version=CURRENT
    )) == "NO_TRUSTED_KEYS"  # fmt: skip


def test_tampered_manifest_fails_signature(
    keypair: tuple[Ed25519PrivateKey, dict[str, bytes]],
) -> None:
    private, keys = keypair
    sig = sign(private, manifest())
    tampered = manifest(
        assets=[{"name": "evil.zip", "platform": "windows-x64", "sha256": "c" * 64, "size": 1}]
    )
    assert code_of(lambda: check(tampered, sig, keys)) == "BAD_SIGNATURE"


def test_signature_from_unknown_or_attacker_key_rejected(
    keypair: tuple[Ed25519PrivateKey, dict[str, bytes]],
) -> None:
    _, keys = keypair
    attacker = Ed25519PrivateKey.generate()
    data = manifest()
    assert code_of(lambda: check(data, sign(attacker, data), keys)) == "BAD_SIGNATURE"
    assert code_of(lambda: check(data, sign(attacker, data, "other"), keys)) == "UNTRUSTED_KEY"


@pytest.mark.parametrize(
    "sig",
    [b"not json", b"{}", b'{"key_id": "test-key-1", "signature": "!!!"}',
     b'{"key_id": "test-key-1", "signature": "AAAA"}', b"x" * 5000],
)  # fmt: skip
def test_malformed_signature_files_rejected(
    keypair: tuple[Ed25519PrivateKey, dict[str, bytes]], sig: bytes
) -> None:
    _, keys = keypair
    assert code_of(lambda: check(manifest(), sig, keys)) in {
        "BAD_SIGNATURE_FILE", "BAD_SIGNATURE", "TOO_LARGE"
    }  # fmt: skip


@pytest.mark.parametrize(
    ("overrides", "target", "code"),
    [
        ({"version": "0.1.0"}, Version.parse("0.1.0"), "DOWNGRADE"),
        ({"version": "0.0.9"}, Version.parse("0.0.9"), "DOWNGRADE"),
        ({"version": "0.3.0-rc.1"}, Version.parse("0.3.0-rc.1"), "DOWNGRADE"),
        ({"version": "0.3.0"}, TARGET, "VERSION_MISMATCH"),
        ({"repository": "attacker/OpenFilm-Studio"}, TARGET, "BAD_MANIFEST"),
        ({"product": "other"}, TARGET, "BAD_MANIFEST"),
        ({"schema": 2}, TARGET, "BAD_MANIFEST"),
        ({"assets": [{"name": "../x.zip", "platform": "windows-x64", "sha256": "b" * 64,
                      "size": 1}]},
         TARGET, "BAD_MANIFEST"),
        ({"assets": [{"name": "x.zip", "platform": "beos", "sha256": "b" * 64, "size": 1}]},
         TARGET, "BAD_MANIFEST"),
        ({"assets": [{"name": "x.zip", "platform": "linux-x64", "sha256": "XYZ", "size": 1}]},
         TARGET, "BAD_MANIFEST"),
        ({"assets": [{"name": "x.zip", "platform": "linux-x64", "sha256": "b" * 64, "size": 0}]},
         TARGET, "BAD_MANIFEST"),
    ],
)  # fmt: skip
def test_signed_but_invalid_manifests_rejected(
    keypair: tuple[Ed25519PrivateKey, dict[str, bytes]],
    overrides: dict[str, Any],
    target: Version,
    code: str,
) -> None:
    private, keys = keypair
    data = manifest(**overrides)
    assert code_of(lambda: check(data, sign(private, data), keys, target)) == code


# --- artifacts --------------------------------------------------------------------


def make_asset(content: bytes) -> ManifestAsset:
    return ManifestAsset("a.zip", "linux-x64", hashlib.sha256(content).hexdigest(), len(content))


def test_artifact_checksum_and_size(tmp_path: Path) -> None:
    good = tmp_path / "a.zip"
    good.write_bytes(b"release-bytes")
    verify_artifact(good, make_asset(b"release-bytes"))

    partial = tmp_path / "partial.zip"
    partial.write_bytes(b"release-")
    assert (
        code_of(lambda: verify_artifact(partial, make_asset(b"release-bytes"))) == "SIZE_MISMATCH"
    )

    corrupt = tmp_path / "corrupt.zip"
    corrupt.write_bytes(b"RELEASE-BYTES")
    assert (
        code_of(lambda: verify_artifact(corrupt, make_asset(b"release-bytes")))
        == "CHECKSUM_MISMATCH"
    )


# --- extraction --------------------------------------------------------------------


def zip_with(tmp_path: Path, entries: list[tuple[str, bytes, int | None]]) -> Path:
    path = tmp_path / "update.zip"
    with zipfile.ZipFile(path, "w") as zf:
        for name, data, mode in entries:
            info = zipfile.ZipInfo(name)
            if mode is not None:
                info.external_attr = mode << 16
            zf.writestr(info, data)
    return path


def test_safe_zip_extracts_into_staging(tmp_path: Path) -> None:
    archive = zip_with(tmp_path, [("app/main.py", b"print()", None), ("README.md", b"hi", None)])
    dest = tmp_path / "staging"
    written = safe_extract(archive, dest)
    assert sorted(p.relative_to(dest).as_posix() for p in written) == ["README.md", "app/main.py"]


@pytest.mark.parametrize(
    "entry",
    [
        ("../escape.txt", b"x", None),
        ("app/../../escape.txt", b"x", None),
        ("/etc/evil", b"x", None),
        ("C:/Windows/evil.dll", b"x", None),
        ("..\\escape.txt", b"x", None),
        ("link", b"/etc/passwd", stat.S_IFLNK | 0o777),
        ("fifo", b"", stat.S_IFIFO | 0o644),
    ],
)
def test_malicious_zip_entries_rejected_and_nothing_written(
    tmp_path: Path, entry: tuple[str, bytes, int | None]
) -> None:
    archive = zip_with(tmp_path, [("ok.txt", b"ok", None), entry])
    dest = tmp_path / "staging"
    assert code_of(lambda: safe_extract(archive, dest)) == "UNSAFE_ARCHIVE"
    assert list(dest.iterdir()) == []
    assert not (tmp_path / "escape.txt").exists()


def test_zip_bomb_and_entry_limits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    archive = zip_with(tmp_path, [("big.bin", b"0" * 5000, None)])
    monkeypatch.setattr(verify, "MAX_EXTRACTED_BYTES", 1000)
    assert code_of(lambda: safe_extract(archive, tmp_path / "s1")) == "UNSAFE_ARCHIVE"
    monkeypatch.setattr(verify, "MAX_EXTRACTED_BYTES", 10**9)
    monkeypatch.setattr(verify, "MAX_ARCHIVE_ENTRIES", 0)
    assert code_of(lambda: safe_extract(archive, tmp_path / "s2")) == "UNSAFE_ARCHIVE"


def tar_with(tmp_path: Path, members: list[tarfile.TarInfo]) -> Path:
    path = tmp_path / "update.tar.gz"
    with tarfile.open(path, "w:gz") as tf:
        for info in members:
            tf.addfile(info, io.BytesIO(b"x" * info.size) if info.isfile() else None)
    return path


def test_tar_links_and_traversal_rejected(tmp_path: Path) -> None:
    ok = tarfile.TarInfo("app/ok.txt")
    ok.size = 1
    link = tarfile.TarInfo("app/link")
    link.type = tarfile.SYMTYPE
    link.linkname = "/etc/passwd"
    escape = tarfile.TarInfo("../escape.txt")
    escape.size = 1
    assert safe_extract(tar_with(tmp_path, [ok]), tmp_path / "t0")
    for bad in (link, escape):
        (tmp_path / "update.tar.gz").unlink()
        archive = tar_with(tmp_path, [ok, bad])
        dest = tmp_path / f"t-{bad.name.replace('/', '_').replace('.', '_')}"
        assert (
            code_of(lambda archive=archive, dest=dest: safe_extract(archive, dest))
            == "UNSAFE_ARCHIVE"
        )
    assert not (tmp_path / "escape.txt").exists()


def test_extraction_refuses_non_empty_staging_and_unknown_formats(tmp_path: Path) -> None:
    staging = tmp_path / "staging"
    staging.mkdir()
    (staging / "existing").write_text("x")
    archive = zip_with(tmp_path, [("a.txt", b"a", None)])
    assert code_of(lambda: safe_extract(archive, staging)) == "UNSAFE_ARCHIVE"
    exe = tmp_path / "setup.exe"
    exe.write_bytes(b"MZ\x90\x00")
    assert code_of(lambda: safe_extract(exe, tmp_path / "s3")) == "UNSAFE_ARCHIVE"
