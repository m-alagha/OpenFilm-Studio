# Master implementation plan

## Product goal
An open-source local-first film studio where each film/series has its own character library, location library, voice assignments, scripts, scenes, references, generated takes, timeline, exports and usage budget. Easy GitHub install; configure eligible provider API credentials locally; no mandatory account or hosted backend.

**Local-first guarantee:** by default, all of the following stay on the user's device:

- projects, characters, locations, voices and reference files
- generated media and all metadata
- application settings
- credentials, which go in the OS credential store

Only the minimum inputs a generation needs are sent, only to the provider the user selected, and only after the user has seen exactly what will be sent and authorized it. See `docs/ARCHITECTURE.md` § Local-first guarantees.

## Milestone protocol
One milestone at a time, in order M0, M1, M1.5, M2 … M11. M1.5 was added after M0 so existing numbering is preserved. Each has deliverables, tests, acceptance gate. Stop after each. Do not skip. Use mock provider until real provider integration is verified.

### M0 — Provider feasibility and repository foundation
- Verify actual official Google video model/product/API names, availability, required billing/allowlisting, input/output constraints, reference image/video support, duration/resolution, pricing and usage/balance APIs. Record URL, access date and confidence in `docs/PROVIDER_CAPABILITIES.md`.
- If the named model is not officially documented or accessible, explicitly say so; select a verified compatible Google video model only with user approval. Never invent endpoints.
- Scaffold repo, license choice decision (Apache-2.0 proposed, confirm rights), gitignore, Python/Node toolchain, lint/test scripts, README and env example.
- Acceptance: official evidence matrix or clearly blocked items; mock smoke test; clean install steps; no secrets in git.

### M1 — Local app bootstrap and one-command startup
- React/TypeScript/Vite + Tailwind frontend; FastAPI backend; SQLite with Alembic; media directories; start script for macOS/Linux/Windows instructions; health endpoints.
- **App/data separation (foundation for M1.5):**
  - User data lives in the OS user-data directory, never inside the install or git checkout. `OPENFILM_DATA_DIR` overrides it.
  - The app version and DB schema version are recorded.
  - Startup refuses to open a DB whose schema is newer than the app supports.
- Acceptance: fresh clone -> documented setup -> browser opens; automated backend/frontend smoke tests; no API key needed for mock; tests prove no user data is written inside the app directory.

### M1.5 — In-app update manager (mandatory)

**Update check**
- A background check against the project's GitHub Releases. Stable releases only; drafts and prereleases are ignored.
- The GitHub API contract (endpoint, fields, rate limits) must be verified against official docs at implementation time. Do not code it from memory.
- The check runs after startup, never blocks it, and uses a short timeout and a cached result.
- Offline, rate-limited or failed checks are silent. They are logged locally only.
- The request carries only the repository path and a generic User-Agent. It never sends projects, media, settings, identifiers or API keys.

**Version comparison**
- SemVer 2.0 comparison. Invalid tags are ignored.

**Notification**
- An in-app notification shows the new version, sanitized release notes, and update size when the release provides it.
- Actions: **Update Now**, **Remind Me Later** (snooze), **Skip Version** (persisted; a newer version shows again).

**Settings**
- Enable or disable automatic checks, plus a "Check now" button.
- Disclosed during first-run onboarding.
- `OPENFILM_UPDATE_CHECK=0` disables checks for CI and air-gapped use.

**Install-type detection, and safe update paths for each**
- **Git checkout:** show instructions (clean-tree check, fetch tags, verify tag, checkout, reinstall with lockfiles, migrate). An optional approved one-click flow is allowed only when the working tree is clean and the tag is verified.
- **Docker:** show instructions only (pull pinned image tag or digest, recreate the container; data stays on its volume). The app never controls Docker from inside the container.
- **Release archive:** one-click update where technically possible:
  1. Download to a staging directory.
  2. Verify the SHA-256 checksum and the release signature. The signing method is chosen and verified at M1.5 and published by M11.
  3. Extract safely (no zip-slip or symlinks).
  4. Install side by side as a new versioned app directory.
  5. Switch to it only after a health check.

**Data preservation**
- Updates never modify the user-data directory, except for DB migrations.
- Before any migration, take a consistent SQLite backup (online backup API), record its checksum and verify it.
- Migrations run in a transaction.
- The OS keychain credentials are never touched.

**Recovery and rollback**
- Keep the previous app version and the pre-migration backup.
- If an install, migration or health check fails, restore both automatically where possible. Otherwise show exact manual recovery steps.
- Keep a configurable number of backups.

**Acceptance**
Automated tests cover:
- version comparison
- update detection against mocked responses: newer, same, older, prerelease, draft, skipped, snoozed, disabled, offline, timeout, rate limit, malformed data
- failed updates: checksum mismatch, bad signature, partial download, extraction attack, migration failure, health-check failure
- data preservation: byte-identical fixture data directory (DB rows, media, settings) before and after an update
- rollback: app version and DB restored
- privacy: outbound request contains no user data or keys
- non-blocking startup with the network blocked
- no install without an explicit approval action

A full end-to-end archive update between two real releases is re-verified at M11.

### M2 — Projects and asset library
- CRUD projects (film/series, seasons optional), scoped characters, locations, props, outfits, voice profiles; image uploads and reference metadata; import/export safe project bundle.
- Acceptance: two projects have isolated assets; upload validation; round-trip export/import tests.

### M3 — Scene editor and @mentions
- Scenes with ordered shots, character/location selectors, @mentions autocomplete, dialogue with speaker assignment, actions, camera, aspect ratio, duration and reference selectors; autosave and validation.
- Acceptance: scene drafts persist, references resolve only inside project, missing references flagged.

### M4 — Provider adapter and generation queue (mock-first)
- Typed provider interface: capabilities, validate_config, estimate, submit, poll, download, cancel-if-supported. Local job queue, retries/backoff, cancellation semantics, progress and result history.
- Acceptance: mock generation end-to-end; retry/idempotency tests; no duplicate charges on frontend retries.

### M5 — Verified Google video integration
- Implement **only officially supported** Google provider API operations discovered at M0. Secure credential setup, capability-aware UI, paid-call confirmation, polling and artifact storage. Handle quota, permissions and provider errors.
- Acceptance: mocked integration contract tests; opt-in live smoke test using user's own key; document unsupported features. If access blocked, milestone remains blocked, not faked.

### M6 — Continuity and reference workflow
- Character reference sets, location views, last-frame extraction, shot-to-shot handoff, optional prior-video reference only if provider supports it, continuity checklist and manual approval. Automatic checks can flag drift but never guarantee identity.
- Acceptance: reference provenance tracked, unsupported modes disabled, two-scene mock workflow and review screen tested.

### M7 — Voice and dialogue pipeline
- Per-character voice identity metadata; optional pluggable licensed TTS provider, uploaded audio, dialogue timing, voice previews, subtitle generation and lip-sync integration only where verified/authorized. Consent safeguards for cloned voices.
- Acceptance: stable mapping of speaker to voice asset; mock audio pipeline; clear unsupported paths; no unauthorized cloning.

### M8 — Cost center and budget guardrails
- Provider price catalog with verified date/version; estimated vs actual usage ledger, per-project budget, pending-job reservations, cost breakdown, warnings and user-controlled spending caps. Provider account balance only if official API exposes it; otherwise show 'unavailable', never pretend.
- Acceptance: unit tests for estimates, retries, cancellations, concurrency, budget cap and missing billing data; no paid job when app budget exceeded.

### M9 — Timeline, editing and export
- Shot ordering, multiple takes, trim, transitions, captions, soundtrack rights notices, FFmpeg assembly and export MP4 with metadata.
- Acceptance: deterministic sample film exported offline, audio sync and format checks.

### M10 — AI director assistants (optional)
- Prompt compiler, script-to-shot suggestion, scene review, drift detection heuristics, agent approvals and provenance. Agents never autonomously spend money or alter approved assets without confirmation.
- Acceptance: deterministic prompt assembly, review findings, explicit human approval gates.

### M11 — Open-source release and cross-platform hardening
- GitHub Actions CI, security scan, docs, contributor guide, issue templates, demo assets with clear rights, Docker optional, release checklist, sample mock project, backup/restore.
- Release integrity for the M1.5 updater:
  - SemVer tags, with stable vs. prerelease flags set correctly
  - release notes
  - per-asset SHA-256 checksums plus a signature (the method verified at M1.5)
  - a published upgrade-path test
- Acceptance: clean machine onboarding, passing CI, secrets scan, license audit, reproducible demo, tagged release candidate; in-app update from the previous release candidate to the new one preserves a fixture data directory, and rollback works.

## Out of scope for V1
Guaranteed face/voice identity, feature claims without provider support, automatic cloud billing enforcement, unlimited free generation, distributed multiuser hosting, autonomous paid generation.
