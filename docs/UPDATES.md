# In-app update manager (M1.5)

**Official repository:** https://github.com/m-alagha/OpenFilm-Studio. It is the only release source, a build-time constant that cannot be changed from the UI.

## What it does

1. **Checks for new versions.**
   - The engine asks GitHub for the public release list in the background, at most about once a day.
   - No automatic request runs until the user has answered the first-run disclosure (D8, D20).
   - The **Check for Updates** button makes one request when clicked. It does not switch on automatic checks.
2. **Shows a notification.**
   - It appears when a newer **stable** version exists.
   - It shows the current and new versions, plain-text release notes, the release date, and the download size when the release has an asset for this OS and architecture.
3. **Offers four actions:**
   - **How to Update**: the label reads **Update Now** only once automatic installation is supported.
   - **Remind Me Later**: hides the notification for 3 days.
   - **Skip This Version**: hides only that version; newer ones still show.
   - **Settings → Updates**: an auto-check toggle, a manual check, and the last-checked time and result.
4. **Never downloads, installs or runs anything.** One-click installation stays disabled until signed installers exist (D9). The `POST /api/updates/install` endpoint always answers `409 ONE_CLICK_UNSUPPORTED`.

## Supported update methods

| Install type (auto-detected) | Detection | Update method | Status |
|---|---|---|---|
| **Git checkout** | `.git` in the app folder | Guided steps:<br>1. Stop the app.<br>2. Check `origin` is the official repository.<br>3. Check for local changes.<br>4. `git fetch --tags origin`.<br>5. `git checkout vX.Y.Z`.<br>6. Start the app again. The launcher reinstalls dependencies when a lockfile changes. | **Supported (instructions)** |
| **Docker** | `/.dockerenv`, or `OPENFILM_INSTALL_TYPE=docker` | Guided steps: keep the data volume; never use `down -v`; set the image tag; `docker compose pull && docker compose up -d` | **Instructions only.** No official image is published yet (M11) |
| **Source download** (zip, no `.git`) | Fallback | Download the new source zip, extract it into a **new** folder, keep the old one until the new one works | **Supported (instructions)** |
| **Packaged app** | `openfilm-install.json` marker, written by a future installer | Download from the official release page and run the installer | **Instructions only.** No installers exist yet |
| One-click (any type) | — | Download → verify signature and checksum → extract safely → install side by side → health check → switch | **Disabled.** Verification building blocks are implemented and tested (see below). There is no download or installer step, and no trusted release key yet |

**Platforms:**

- Windows, macOS and Linux each get their own commands, for example `scripts\dev.cmd` versus `sh scripts/dev.sh` and `cd /d "…"` versus a shell-quoted `cd`.
- Commands are fixed templates. Only two values are ever inserted: a version that passed strict SemVer validation, and this machine's app path. **Release metadata never reaches a command.**

## Privacy of the update check

- **The request:**
  - `GET https://api.github.com/repos/m-alagha/OpenFilm-Studio/releases?per_page=30`
  - Exactly three headers: `Accept: application/vnd.github+json`, `X-GitHub-Api-Version: 2026-03-10`, and `User-Agent: OpenFilm-Studio-Updater`. The User-Agent carries no version and no identifier.
  - No cookies, no credentials, no body.
- **What GitHub sees:** your IP address, as with any web request.
- **What is never sent:** projects, media, settings, file paths and API keys. A test asserts this.
- **Kill switch:** `OPENFILM_UPDATE_CHECK=0` turns off all update network activity, for CI and air-gapped use.

## Validation of release metadata (untrusted input)

- **Which releases count:** only published (`draft: false`), stable (`prerelease: false`, with a SemVer tag that has no pre-release part) releases are considered. The highest version newer than the running one is offered. Equal or older versions are never offered (no downgrade).
- **Rejected releases:** a release is rejected if any of these hold:
  - its `html_url` isn't `https://github.com/m-alagha/OpenFilm-Studio/releases/tag/<tag>`
  - an asset URL isn't `…/releases/download/<tag>/<name>`
  - an asset name is unsafe (path separators, `..`, a trailing newline)
  - an asset size is invalid
  - a flag isn't a boolean

  The owner/repo part of the URLs is compared case-insensitively.
- **Size limits:**
  - Responses over 2 MB are refused.
  - Redirects are followed only to `https://api.github.com`.
  - At most 100 releases and 50 assets are read.
- **Release notes** are shown as plain text: control and bidi-override characters are stripped, and the text is capped at 20,000 characters. HTML is never rendered.
- **Asset digests:** a `digest` is used only in the exact form `sha256:<64 hex>`. Its format is not documented. It is informational only; authenticity comes from the signed manifest.

## Release authenticity (D9, D18)

**Chosen design: an Ed25519-signed release manifest, verified in the app.**

Each release must publish two files:

- `openfilm-release.json`:

  ```json
  {"schema": 1, "product": "openfilm-studio", "repository": "m-alagha/OpenFilm-Studio",
   "version": "X.Y.Z",
   "assets": [{"name": "...", "platform": "windows-x64", "sha256": "<64 hex>", "size": 123}]}
  ```

- `openfilm-release.json.sig`: `{"key_id": "...", "signature": "<base64 Ed25519 signature over the exact manifest bytes>"}`

**Verification order** (`backend/app/updates/verify.py`):

1. The signature is checked against keys pinned in `TRUSTED_RELEASE_KEYS`. The manifest is parsed only after it passes.
2. The manifest's product, repository and version must match the release, and the version must be stable and newer than the running one.
3. Each asset must have a safe name, a known platform, a valid SHA-256 and a valid size.
4. Downloaded files must match the signed size (which catches partial downloads) and SHA-256.
5. Archives are extracted into an empty staging folder. Absolute paths, drive letters, `..`, backslash traversal, links, device files, too many entries and oversized content are all rejected.
6. Nothing is ever executed.

**No key is trusted yet** (`TRUSTED_RELEASE_KEYS = {}`), so verification fails closed with `NO_TRUSTED_KEYS`. **M11 must:**

- generate the release key offline and store it outside the repository (for example a hardware token or CI secret)
- pin the public key with a `key_id` (multiple keys are supported, for rotation)
- sign each release in CI

**Evaluation of alternatives (sources accessed 2026-11-07):**

| Option | Strengths | Concerns for in-app verification | Decision |
|---|---|---|---|
| **Ed25519 manifest** (via `cryptography`) | Verifies offline. 32-byte pinned key, 64-byte signature. One well-audited dependency (Apache-2.0 / BSD) | The project must manage the signing key itself | **Primary**: verified in the app |
| **Sigstore / GitHub artifact attestations** | Keyless signing tied to the GitHub Actions workflow identity. Public transparency log (public repos). SLSA Build L2/L3 | `sigstore-python` "checks for updates to the trusted key material on every startup" by default, and offline mode needs a bundle and trust-root management. The PyPI page doesn't list its dependencies. Attestations "do not guarantee an artifact is secure" | **Complementary**: generate attestations in CI at M11; users and auditors verify with `gh attestation verify`. Not required by the app |

## Data protection during updates

- **Single instance (data-folder lock):** an OS advisory lock on `<data>/.openfilm.lock`, using `msvcrt` on Windows and `flock` on macOS and Linux.
  - A second engine on the same data folder exits with code 3 ("already running") and never opens the database.
  - The lock is released automatically if the process crashes, so stale lock files never block startup.
  - The recovery tool refuses to run while the app holds the lock.
- **Migrations:**
  - A verified backup is taken before any migration (SQLite online backup, `integrity_check`, and a `.sha256` sidecar).
  - All migrations run in one transaction, with transactional DDL and `BEGIN IMMEDIATE`.
  - If a migration fails, nothing is applied and the backup remains.
- **Newer databases** (from a future version) are refused read-only and never modified.
- **Updates never touch user files.** User data lives outside the app folder. Tests compare a fingerprint of the data folder (media, references, settings files, backups) before and after an update and a rollback.
- **Backups are never deleted automatically.** Pruning a configurable number of backups is deferred, and any pruning will need explicit confirmation.

## Recovery after a failed update

```bash
uv run --project backend python -m app.recovery list
```

```bash
uv run --project backend python -m app.recovery restore <backup-file-name>
```

How `restore` behaves:

- It requires OpenFilm Studio to be closed (it checks the lock).
- It verifies the backup's checksum and that this app can open it.
- It asks you to type `RESTORE`, or accepts `--yes`.
- It first saves the current database as a new verified backup. If that database is damaged, it saves an exact byte copy with a verified SHA-256 instead, so a restore never loses data.
- It builds the restored database in a temporary file, verifies it, then swaps it in atomically. Leftover journal files are moved aside, never deleted.
- It never touches media or other files.

To go back to the previous version of a git install, run `git checkout v<previous>`, then restore the pre-migration backup. The in-app guide shows these rollback steps.

## GitHub REST API evidence (accessed 2026-11-07)

| Fact | Source | Used as |
|---|---|---|
| `GET /repos/{owner}/{repo}/releases`; `per_page` max 100; unauthenticated users don't see drafts | [Releases API](https://docs.github.com/en/rest/releases/releases) | List endpoint, `per_page=30` |
| `/releases/latest` = "most recent non-prerelease, non-draft release, sorted by the created_at attribute" | same | Not used: we pick the highest SemVer ourselves |
| Release fields `tag_name, name, body, draft, prerelease, published_at, html_url, assets`; asset fields include `name, size, browser_download_url, digest (string or null)` | same, plus [Release assets API](https://docs.github.com/en/rest/releases/assets) | Parser fields |
| Asset SHA-256 digests are computed at upload and immutable | [Changelog 2025-06-03](https://github.blog/changelog/2025-06-03-releases-now-expose-digests-for-release-assets/) | Optional, informational |
| API versions `2026-03-10` (no end of support scheduled) and `2022-11-28` (end of support 2028-03-10) | [API versions](https://docs.github.com/en/rest/about-the-rest-api/api-versions) | Pin `2026-03-10` |
| A User-Agent is required; requests without one are rejected | [Getting started](https://docs.github.com/en/rest/using-the-rest-api/getting-started-with-the-rest-api) | `OpenFilm-Studio-Updater` |
| Unauthenticated limit is 60 requests/hour per originating IP; limits return 403 or 429; honor `retry-after` and `x-ratelimit-reset` | [Rate limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api) | Back off until the indicated time (capped at 24 h). Auto checks run at most once a day; manual checks at most once a minute after a success |
| Ed25519 `from_public_bytes` (32 bytes), `verify` raises `InvalidSignature`, 64-byte signatures | [cryptography Ed25519](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/) | `verify.py` |
| Artifact attestations use Sigstore; consumers verify with `gh attestation verify` | [Artifact attestations](https://docs.github.com/en/actions/concepts/security/artifact-attestations) | M11 complementary provenance |
| `sigstore-python` 4.5.1 checks for trusted-root updates on every startup by default; `--offline` needs a bundle | [PyPI sigstore](https://pypi.org/project/sigstore/) | Not used in the app (see evaluation) |

**Unverified:**

- Redirect behavior for renamed repositories is not documented for the REST API. Redirects are allowed only to `api.github.com`.
- The `digest` string format is not documented.
- Nothing here was live-tested against GitHub, because the repository has no releases yet. All tests use mocked responses.
