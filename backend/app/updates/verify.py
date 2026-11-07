"""Release authenticity and integrity verification (D9, D17).

Design: every release publishes ``openfilm-release.json`` (a manifest listing
each asset's SHA-256 and size) plus ``openfilm-release.json.sig`` (an Ed25519
signature over the exact manifest bytes). The app trusts only the public keys
pinned in TRUSTED_RELEASE_KEYS. Order of checks: signature first, then parse.

No key is trusted yet (the release key is created at M11), so verification fails
closed and one-click installation stays disabled. Nothing here executes files.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import shutil
import stat
import tarfile
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from app.updates import REPOSITORY
from app.updates.version import InvalidVersion, Version

MANIFEST_NAME = "openfilm-release.json"
SIGNATURE_NAME = MANIFEST_NAME + ".sig"
MANIFEST_SCHEMA = 1
PRODUCT = "openfilm-studio"
PLATFORMS = frozenset(
    {"windows-x64", "windows-arm64", "macos-x64", "macos-arm64", "linux-x64", "linux-arm64"}
)
MAX_MANIFEST_BYTES = 64 * 1024
MAX_SIGNATURE_BYTES = 1024
MAX_ARTIFACT_BYTES = 4 * 1024**3
MAX_ARCHIVE_ENTRIES = 20_000
MAX_EXTRACTED_BYTES = 8 * 1024**3

# key_id -> raw 32-byte Ed25519 public key. Empty until the M11 key ceremony.
TRUSTED_RELEASE_KEYS: Mapping[str, bytes] = {}

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,199}$")


class VerificationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


@dataclass(frozen=True)
class ManifestAsset:
    name: str
    platform: str
    sha256: str
    size: int


@dataclass(frozen=True)
class ReleaseManifest:
    version: Version
    assets: tuple[ManifestAsset, ...]

    def asset_for(self, platform: str) -> ManifestAsset | None:
        return next((a for a in self.assets if a.platform == platform), None)


def verify_manifest(
    manifest_bytes: bytes,
    signature_bytes: bytes,
    *,
    expected_version: Version,
    current_version: Version,
    trusted_keys: Mapping[str, bytes] = TRUSTED_RELEASE_KEYS,
) -> ReleaseManifest:
    if not trusted_keys:
        raise VerificationError("NO_TRUSTED_KEYS", "no release signing key is trusted yet")
    if len(manifest_bytes) > MAX_MANIFEST_BYTES or len(signature_bytes) > MAX_SIGNATURE_BYTES:
        raise VerificationError("TOO_LARGE", "manifest or signature too large")
    try:
        sig_doc = json.loads(signature_bytes)
        key_id = sig_doc["key_id"]
        signature = base64.b64decode(sig_doc["signature"], validate=True)
    except (ValueError, KeyError, TypeError) as exc:
        raise VerificationError("BAD_SIGNATURE_FILE", "signature file is malformed") from exc
    if not isinstance(key_id, str) or key_id not in trusted_keys:
        raise VerificationError("UNTRUSTED_KEY", "manifest signed by an unknown key")
    if len(signature) != 64:
        raise VerificationError("BAD_SIGNATURE", "signature has the wrong length")
    try:
        Ed25519PublicKey.from_public_bytes(trusted_keys[key_id]).verify(signature, manifest_bytes)
    except InvalidSignature:
        raise VerificationError("BAD_SIGNATURE", "manifest signature is invalid") from None

    # Only now is the manifest content trusted enough to parse.
    try:
        doc = json.loads(manifest_bytes)
        version = Version.parse(doc["version"])
        assets_raw = doc["assets"]
        ok = (
            doc["schema"] == MANIFEST_SCHEMA
            and doc["product"] == PRODUCT
            and doc["repository"] == REPOSITORY
            and isinstance(assets_raw, list)
        )
    except (ValueError, KeyError, TypeError, InvalidVersion) as exc:
        raise VerificationError("BAD_MANIFEST", "manifest is malformed") from exc
    if not ok:
        raise VerificationError("BAD_MANIFEST", "manifest is for another product or repository")
    if version != expected_version:
        raise VerificationError("VERSION_MISMATCH", "manifest version differs from the release")
    if not version.is_stable or not version > current_version:
        raise VerificationError("DOWNGRADE", "only newer stable versions can be installed")
    return ReleaseManifest(version, tuple(_manifest_asset(a) for a in assets_raw))


def _manifest_asset(raw: object) -> ManifestAsset:
    if not isinstance(raw, dict):
        raise VerificationError("BAD_MANIFEST", "asset entry is not an object")
    name, platform, digest, size = (
        raw.get("name"),
        raw.get("platform"),
        raw.get("sha256"),
        raw.get("size"),
    )
    if not isinstance(name, str) or not _SAFE_NAME.fullmatch(name) or ".." in name:
        raise VerificationError("BAD_MANIFEST", "unsafe asset name")
    if platform not in PLATFORMS:
        raise VerificationError("BAD_MANIFEST", "unknown platform")
    if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
        raise VerificationError("BAD_MANIFEST", "invalid sha256")
    if type(size) is not int or not 0 < size <= MAX_ARTIFACT_BYTES:
        raise VerificationError("BAD_MANIFEST", "invalid size")
    return ManifestAsset(name, str(platform), digest, size)


def verify_artifact(path: Path, asset: ManifestAsset) -> None:
    """Size first (catches partial downloads), then SHA-256."""
    size = path.stat().st_size
    if size != asset.size:
        raise VerificationError("SIZE_MISMATCH", f"expected {asset.size} bytes, got {size}")
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    if digest.hexdigest() != asset.sha256:
        raise VerificationError("CHECKSUM_MISMATCH", "artifact does not match the signed checksum")


def _check_member_name(name: str) -> PurePosixPath:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        not normalized
        or path.is_absolute()
        or ".." in path.parts
        or re.match(r"^[A-Za-z]:", normalized)
        or "\x00" in normalized
    ):
        raise VerificationError("UNSAFE_ARCHIVE", f"unsafe path in archive: {name[:100]!r}")
    return path


def safe_extract(archive: Path, dest: Path) -> list[Path]:
    """Extract a verified zip or tar.gz into an empty staging directory.

    Rejects absolute paths, drive letters, '..', links, devices, too many entries
    and oversized content (zip bombs). Files are written, never executed.
    """
    if dest.exists() and any(dest.iterdir()):
        raise VerificationError("UNSAFE_ARCHIVE", "staging directory is not empty")
    dest.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    total = 0
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as zf:
            members = zf.infolist()
            if len(members) > MAX_ARCHIVE_ENTRIES:
                raise VerificationError("UNSAFE_ARCHIVE", "too many entries")
            for info in members:
                _check_member_name(info.filename)
                mode = info.external_attr >> 16
                # zipfile stores bare permission bits (no type) for ordinary files.
                if stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR):
                    raise VerificationError(
                        "UNSAFE_ARCHIVE", "links and special files are not allowed"
                    )
                total += info.file_size
                if total > MAX_EXTRACTED_BYTES:
                    raise VerificationError(
                        "UNSAFE_ARCHIVE", "archive expands beyond the size limit"
                    )
            for info in members:
                target = dest.joinpath(*_check_member_name(info.filename).parts)
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as src, target.open("wb") as out:
                    shutil.copyfileobj(src, out, 1 << 20)
                written.append(target)
        return written
    if tarfile.is_tarfile(archive):
        with tarfile.open(archive) as tf:
            tar_members = tf.getmembers()
            if len(tar_members) > MAX_ARCHIVE_ENTRIES:
                raise VerificationError("UNSAFE_ARCHIVE", "too many entries")
            for member in tar_members:
                _check_member_name(member.name)
                if not (member.isfile() or member.isdir()):
                    raise VerificationError(
                        "UNSAFE_ARCHIVE", "links and special files are not allowed"
                    )
                total += member.size
                if total > MAX_EXTRACTED_BYTES:
                    raise VerificationError(
                        "UNSAFE_ARCHIVE", "archive expands beyond the size limit"
                    )
            tf.extractall(dest, filter="data")  # second line of defence
            written = [
                dest.joinpath(*PurePosixPath(m.name).parts) for m in tar_members if m.isfile()
            ]
        return written
    raise VerificationError("UNSAFE_ARCHIVE", "unsupported archive format")
