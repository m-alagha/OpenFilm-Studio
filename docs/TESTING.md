# Testing and acceptance policy

Backend: pytest, FastAPI TestClient, schema/migration tests, provider mock contract tests. Frontend: Vitest + React Testing Library, Playwright happy-path e2e. Tooling: ruff, mypy where useful, ESLint, TypeScript check, secret scanning. FFmpeg export tests on generated fixtures.

Required checks per milestone: unit tests, integration tests, user flow, failure paths, data isolation, no leaked keys, zero real provider cost unless explicitly approved. Test permission failures, missing API key, offline mode, rate limits, retries, invalid uploads, unsafe paths, partial downloads, crashes and restarts. Verify cost ledger never double-counts duplicate retries and blocks new jobs on reserved budget. Include exact command output in reports.

Each milestone report must contain: scope, commits/diff, tests run/pass/fail, manual verification, screenshots when UI, blockers, unsupported capabilities, API charges incurred, security review, and STOP for approval.

## Update manager tests (M1.5, mandatory)

| Area | What the tests must cover |
|---|---|
| Version comparison | SemVer ordering, including prerelease and build metadata. Invalid tags are ignored |
| Update detection | Mocked GitHub responses: newer, equal, older, draft, prerelease, skipped version, snoozed, checks disabled (setting and `OPENFILM_UPDATE_CHECK=0`), offline, timeout, HTTP 403/429 rate limit, malformed JSON |
| Failed updates | Checksum mismatch, invalid signature, partial or interrupted download, disk full, zip-slip or symlink archive, migration failure, health-check failure |
| Data preservation | A fixture user-data directory (SQLite rows, media files, settings, backups) is byte-identical after an update and after a rollback. The only exception is migrated DB content, which must be verified by row checks |
| Rollback | The previous app version and the pre-migration DB backup are both restored, and the app starts |
| Privacy | The captured outbound request contains no user data, keys or identifiers |
| Non-blocking | The app starts and works fully with the network blocked and checks enabled |
| Approval | No code path installs without the explicit approve action |
