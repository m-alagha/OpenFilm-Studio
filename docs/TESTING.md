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

## Release-gate tests (assigned milestones)

| Requirement | Milestone | What must be proven |
|---|---|---|
| Data-directory lock | M1.5 | Real-process tests: a second instance is refused without touching the DB; no update or migration while locked; a crashed holder's lock does not block startup |
| Persistent storage across updates | M1.5 (update tests), M11 (each real install type) | User-data directory and credentials unchanged after update and rollback, apart from verified migrations |
| Persistent storage across uninstall | M11 | For each installer: uninstall keeps the data folder by default; removing it needs an explicit confirmed choice; reinstall reuses it. MSIX is blocked unless proven safe (`docs/RELEASE.md`) |
| Cross-platform runtime | M11 | CI matrix on Windows, macOS and Linux runs `scripts/check.*`, `dev --smoke` and the update/rollback suite. Simulated-platform unit tests are not enough |
| One-click install, failed-install rollback, disk-full and health-check failure, backup retention (deferred from M1.5, D22) | M11 (gate) | Real signed packages installed and rolled back on each OS; retention never removes the newest verified backups |
| Browser-level E2E | M11 (gate), may start earlier | Playwright (or equivalent) with real browsers against the real backend: first run, loading/error/offline states, persistence across restart, newer-database refusal, update notification. M1 has only an HTTP-level E2E (`scripts/e2e_smoke.py`) plus manual browser checks |

From M1 on, `scripts/e2e_smoke.py` also snapshots every file in the checkout before and after a full run, and fails if any file appears inside the app or repository.

### M1.5 coverage of the update-manager table

**Database-safety regressions** (`backend/tests/test_database_safety.py`, added in the final review):

- No SQLite write transaction is open while GitHub is contacted (manual, automatic and API paths). Checked with a zero-timeout writer.
- Concurrent update checks plus readers never deadlock, and the network is called one request at a time.
- Background loop and parallel API checks together return only 200 responses.
- The lock is released after app shutdown and after a normal process exit.
- Restore aborts with the database untouched if a safety copy can't be made.
- A corrupt current database is preserved byte for byte, with its checksum verified, before restore.
- Leftover journals are moved aside, never replayed or deleted.

Every area in the table above is covered by `backend/tests/test_update_*.py`, `test_datalock_recovery.py`, `test_server_process.py`, and `frontend/src/components/updates/UpdateCenter.test.tsx`. Exceptions:

- **"Disk full" and "health-check failure"** cannot be tested, because no download or install step exists yet: one-click is disabled (D21). They move to M11 together with one-click installation.
- **"Rollback: previous app version restored"** is covered by guided git steps plus a tested DB restore. Automatic app-folder rollback needs one-click and moves to M11.
