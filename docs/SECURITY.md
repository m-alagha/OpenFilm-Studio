# Security and privacy

Default local-only server on loopback. Credentials stored in OS keychain when practical; otherwise encrypted local secret store with clear threat model. Never store API keys in frontend localStorage, git, logs, exported project bundles or screenshots. `.env` only for dev with `.gitignore`; `.env.example` placeholders only. Redact provider errors and logs.

Validate file size, MIME and magic bytes; avoid executable uploads, traversal, zip-slip, symlink escapes, SSRF through remote references and FFmpeg unsafe paths. Escape user-provided prompts in UI; do not execute script text. Import/export with explicit media rights, checksums and schema versions. Consent required for voice cloning and identifiable likenesses; follow provider policy. No default analytics, no third-party uploads except selected generation provider, show what media is sent. Provide data delete/backup controls. Confirm paid requests and protect against accidental loops.

## Update security (M1.5)

**Update checks**
- Update checks send only an anonymous request for public release metadata.
- They never send projects, media, settings, machine identifiers or keys.
- They use HTTPS only, and a fixed host that is not user-configurable from the UI.
- Release notes are rendered as sanitized text or Markdown. Raw HTML is never rendered.

**Downloaded artifacts**
- An artifact must match a published SHA-256 checksum *and* a verified signature before it is extracted. Otherwise it is discarded.
- Extraction rejects absolute paths, `..`, symlinks and device files (no zip-slip).
- Staging happens inside the app area, never in the user-data directory.

**Approval and isolation**
- No silent or automatic installs. Every install needs an explicit click in the UI.
- Git and Docker installs get instructions rather than self-modification.
- Updates never read or rewrite the OS credential store.

**Data safety**
- DB backups and migrations are atomic.
- Backups are checksummed. They are excluded from exports unless the user selects them, and they never contain API keys.

### Implementation status (M1.5)

All of the following are implemented and tested:

- **Fixed, anonymous request:** three headers; no cookies, credentials or identifiers.
- **Strict validation:** malformed or off-repository release metadata is rejected.
- **Plain-text release notes:** control and bidi characters stripped.
- **Redirects:** followed only to `api.github.com`.
- **Response cap:** 2 MB.
- **Commands:** built only from fixed templates plus a validated version.
- **No downgrades:** only newer stable versions are offered.
- **Authenticity:** Ed25519 manifest verification, fail-closed with no trusted key yet.
- **Integrity:** checksum and size checks.
- **Extraction:** zip-slip, link and zip-bomb rejection.
- **Install refusal:** an install request is always refused (409).
- **Single-instance lock.**
- **Restore safety:** a restore keeps a copy of the current database.

**Regression found during M1.5:** `re.match(... $)` accepts a trailing newline. Every whole-string validation now uses `fullmatch`, with tests.
