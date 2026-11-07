# Security and privacy

Default local-only server on loopback. Credentials stored in OS keychain when practical; otherwise encrypted local secret store with clear threat model. Never store API keys in frontend localStorage, git, logs, exported project bundles or screenshots. `.env` only for dev with `.gitignore`; `.env.example` placeholders only. Redact provider errors and logs.

Validate file size, MIME and magic bytes; avoid executable uploads, traversal, zip-slip, symlink escapes, SSRF through remote references and FFmpeg unsafe paths. Escape user-provided prompts in UI; do not execute script text. Import/export with explicit media rights, checksums and schema versions. Consent required for voice cloning and identifiable likenesses; follow provider policy. No default analytics, no third-party uploads except selected generation provider, show what media is sent. Provide data delete/backup controls. Confirm paid requests and protect against accidental loops.
