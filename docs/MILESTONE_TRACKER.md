# Milestone tracker

Statuses: NOT_STARTED, IN_PROGRESS, BLOCKED, ACCEPTED. Only user approves ACCEPTED.

Order: M0 → M1 → M1.5 → M2 … M11. M1.5 was inserted on 2026-11-07 at the maintainer's request, without renumbering the other milestones.

| Milestone | Status | Evidence | Approval |
|---|---|---|---|
| M0 | ACCEPTED | See "M0 evidence" below | Maintainer, 2026-11-07, with conditions D1 and D3 |
| M1 | ACCEPTED | See "M1 evidence" below | Maintainer, 2026-11-07, after final checks (repository identity, local-first audit, cleanup) |
| M1.5 | ACCEPTED | See "M1.5 evidence" below | Maintainer, 2026-11-07, conditional approval and final review; deferred items are M11 gates (D22) |
| M2 | NOT_STARTED | — | — |
| M3 | NOT_STARTED | — | — |
| M4 | NOT_STARTED | — | — |
| M5 | NOT_STARTED | — | — |
| M6 | NOT_STARTED | — | — |
| M7 | NOT_STARTED | — | — |
| M8 | NOT_STARTED | — | — |
| M9 | NOT_STARTED | — | — |
| M10 | NOT_STARTED | — | — |
| M11 | NOT_STARTED | — | — |

After each milestone record commit, commands and pass counts, screenshots (if applicable), verified provider links, spend, blockers, and user approval. Never mark ACCEPTED just because code was written.

## M0 evidence (2026-11-07)

**Commit:** `0bbecba` ("M0: provider feasibility evidence and repository foundation").

### Provider verification (docs only, no live calls)

`docs/PROVIDER_CAPABILITIES.md` has 9 official sources, all accessed 2026-11-07.

- `gemini-omni-1.2-flash` exists. Google labels it Stable on the Gemini Developer API (Interactions API).
- Paid tier only.
- Video output is about $0.07/s at 720p ($12 per 1M output tokens).
- Not available through the API:
  - audio or voice input, and voice locking
  - a balance API
  - hard spend caps
  - a documented cancel
- Request and response field names are MEDIUM confidence. Re-verify them at M5.

### Checks run

| Check | Command | Result |
|---|---|---|
| Secret scan | `python scripts/check_secrets.py` | 46 files, 0 findings |
| Backend lint | `ruff check . ../scripts` | All checks passed |
| Backend format | `ruff format --check . ../scripts` | 12 files already formatted |
| Backend types | `mypy` (strict) | no issues in 11 source files |
| Backend tests | `pytest` | **31 passed**, 0 failed. Network is blocked by an autouse fixture |
| Mock smoke test | `python -m app.smoke` | estimate $0 → submit → running 50% → succeeded → `*.mock.json`. MOCK SMOKE TEST PASSED |
| Frontend | `npm run check` (ESLint, `tsc --noEmit`, Vitest) | **5 passed** |
| All checks, bash | `bash scripts/check.sh` | ALL CHECKS PASSED |
| All checks, PowerShell | `scripts\check.ps1` | ALL CHECKS PASSED |

**Clean install:** the files git would ship (46) were copied to an empty directory. There, `uv sync --frozen --extra dev`, `npm ci` and `scripts/check.sh` all passed.

### Spend and screenshots

- **Spend:** $0.00. No provider API calls, and no API key was used or requested.
- **Screenshots:** none, because M0 has no UI.

### Known issues

- `npm audit` reports 10 moderate findings. All come from one advisory, the minimatch ReDoS GHSA-g3hv-75wg-m249. It sits in the dev-only ESLint and typescript-eslint chain, which is not shipped. The only fix offered is downgrading ESLint to 9. Revisit at M11.
- Python 3.11 on this machine is a Microsoft Store alias that uv cannot use, so testing used Python 3.12.
- This machine's network inspects TLS, so uv needs `--native-tls`. This is documented in the README troubleshooting section.

### Approval (2026-11-07)

The maintainer approved M0 with these conditions:

1. **License (D1):** Apache-2.0 applies to original code and docs the maintainer owns or may license. A third-party license audit was added in `docs/THIRD_PARTY_NOTICES.md`: no runtime dependencies; dev dependencies are MIT, BSD, ISC, Apache-2.0, PSF-2.0, BlueOak-1.0.0 and MPL-2.0, all compatible.
2. **Provider (D3):** `gemini-omni-1.2-flash` via the Gemini Developer API is the **provisional** M5 target. M5 must re-verify the raw docs, schemas, availability and pricing first. No paid request without explicit permission.

All checks were re-run before the M0 commit and passed.

## M1 evidence (2026-11-07)

**Commits:**

- `900202a` ("add", committed by the maintainer): the reviewed M1 implementation, 68 files. It was verified after the fact to contain no build output, databases, logs or key-shaped strings.
- A follow-up "M1 final checks" commit holds: the tracker set to ACCEPTED; the official-repository references; release-gate assignments; the stricter repository-snapshot E2E check; and the package-lock root version sync.

Git history and remotes were not rewritten. Nothing was pushed by Claude.

**Decisions recorded:** D8 and D9 are accepted as directed. D10–D14 were made during M1 and are pending review (see `docs/DECISIONS.md`).

### Acceptance criteria

| # | Criterion | Evidence |
|---|---|---|
| 1 | React + TypeScript + Vite frontend (plus Tailwind, per MASTER_PLAN) | `frontend/src/*`. React 19, Vite 8, Tailwind 4, strict TypeScript. `npm run build` OK (227 kB JS, 71 kB gzip) |
| 2 | Modular FastAPI backend | `backend/app/{main,config,paths,security,logging_setup}.py`, plus `api/` and `db/` packages. M0 `providers/` unchanged |
| 3 | Local SQLite with versioned migrations | Alembic `0001_app_meta`, `0002_app_settings`. Forward-only and transactional. `test_models_match_migrations` passes (models and migrations have no drift) |
| 4 | OS data directory outside the repository | `paths.py`, with per-OS tests (Windows `LOCALAPPDATA`, macOS, Linux and XDG). Data directories inside the app are refused, both unit-tested and on a real process. Real run: `C:\Users\PC\AppData\Local\OpenFilmStudio` |
| 5 | App version and schema version tracking | `app_meta` holds `schema_version`, `created_by_app_version`, `last_opened_app_version` and timestamps. `/api/system` reports them |
| 6 | Refuse databases from newer versions | Unknown revision, higher `schema_version`, foreign or corrupt files: all refused, and the SHA-256 is unchanged. The engine stays up in a blocked state (HTTP 503 `DB_NEWER_SCHEMA`) and the UI explains it (screenshot 03) |
| 7 | One-command dev startup | `sh scripts/dev.sh` / `scripts\dev.cmd`. Both pass `--smoke` on this machine, including custom ports. A clean copy with no venv and no node_modules installs dependencies and starts with one command |
| 8 | Localhost-only binding by default | Default `127.0.0.1`. Non-loopback refused (exit 2) without explicit opt-in. A real process test showed the server unreachable on this machine's LAN addresses `192.168.1.57` and `172.31.224.1` |
| 9 | Secure frontend–backend communication | Same-origin proxy and no CORS. Host allowlist against DNS rebinding, Origin check, `X-OpenFilm-Client` required on writes, security headers. 24 API tests, plus E2E checks through the proxy |
| 10 | Loading, error and offline states | UI tests cover loading, unreachable (with auto-retry and manual retry), incompatible database, save failure and the offline banner. Screenshots 01–03 |
| 11 | Windows, macOS, Linux | Path logic is tested for all three OSes. Launchers exist in `.sh` and `.cmd`. **Executed on Windows 11 only**, under both cmd and Git Bash. macOS and Linux are not executed (no CI until M11) |
| 12 | Installation and troubleshooting docs | README: requirements, one-command start, data locations, environment variables, and a troubleshooting table |
| 13 | Automated backend and frontend tests | Backend **96 passed**: 65 new plus 31 from M0. Frontend **19 passed**: 14 new plus 5 from M0 |
| 14 | M0 provider contract and mock preserved | `backend/app/providers/` unchanged. All 17 mock-provider tests and the smoke test pass. `/api/system` reports the mock provider |

### Quality gates

| Gate | Result |
|---|---|
| `bash scripts/check.sh` | ALL CHECKS PASSED |
| `scripts\check.ps1` | ALL CHECKS PASSED |
| Clean-install copy (97 files): `scripts/dev.sh --smoke`, then `scripts/check.sh` | Both passed |
| Persistence across restarts | Covered three ways: an API test with two app instances; a real-process test (write, terminate, restart, read); and E2E through the proxy with a backend restart. Also checked manually in the browser on the real data directory |
| Migration behaviour | Fresh DB created at head; reopening at head is a no-op; upgrade from 0001 takes a verified backup and preserves data; an injected failing migration rolls back fully and the backup remains |
| Lint, format, types | ruff, ruff format, mypy `--strict` (40 files), ESLint (with `no-console`), `tsc` for app and config |
| Secret scan | 97 files, 0 findings |

**Per-file test counts**

- Backend: `test_api` 24, `test_paths_config` 24, `test_mock_provider` 17, `test_migrations` 11, `test_redaction` 7, `test_secret_scan` 5, `test_server_process` 4, `test_logging_deps` 2, `test_smoke` 2
- Frontend: `App.test` 8, `client.test` 6, `costLabel.test` 5

### Screenshots

In `docs/screenshots/m1/`:

- `01-ready.jpg`
- `02-backend-unreachable.jpg`
- `03-newer-database-refused.jpg`

### Spend and security

- **Spend:** $0.00. No provider calls and no API keys. The network is blocked in tests except loopback.
- **License re-audit:** see `docs/THIRD_PARTY_NOTICES.md`. All runtime dependencies are permissive (MIT, BSD-3, Apache-2.0, PSF-2.0).
- **`opentelemetry-api`** is accepted as a FastAPI dependency (D14). It is the no-op API, and a test forbids installing an SDK or exporter.
- **Starlette 1.10 deprecation:** the dev dependency `httpx` was replaced by `httpx2` (BSD-3, maintained by the Pydantic org). The test client now raises no warnings.

### Defects found and fixed during M1

1. **Migrations were not atomic.** pysqlite auto-committed DDL, so a failed migration could leave the database half-applied. Fixed with SQLAlchemy's transactional pysqlite recipe, and covered by the failing-migration test.
2. **XDG path check used host-OS rules.** On Windows, an absolute Linux path was treated as relative. Fixed by using `PurePosixPath`, caught by the per-OS test.
3. **Stale-result race in the UI retry hook.** An earlier attempt could overwrite newer state. Fixed with a per-attempt guard.
4. **Garbled launcher text on the Windows console.** The `…` character didn't render. Replaced with plain ASCII.
5. **Incompatible-database message.** It started lowercase and repeated itself. Polished.

### Final checks before acceptance (2026-11-07)

**Repository identity**

- The official repository is https://github.com/m-alagha/OpenFilm-Studio (D15).
- No project file referenced the old owner `mousa-alagha`. The only occurrences are in git reflogs under `.git/logs`, which are history metadata and were left untouched as instructed. The `origin` remote already pointed to `m-alagha` and was not changed.
- Added the official URL to: the README clone command, backend `[project.urls]`, frontend `homepage`, `repository` and `bugs`, and the M1.5 release source (MASTER_PLAN, RELEASE, CLAUDE.md).

**Local-first audit**

Every persistent write site in the app code resolves inside the data directory:

- `db/engine.py`: the database
- `db/backup.py`: `backups/`
- `logging_setup.py`: `logs/`
- `paths.py`: creates the data directory and refuses locations inside the app

The UI uses no browser storage. The mock provider's `download(dest_dir)` is a developer tool and is not wired into the app.

`scripts/e2e_smoke.py` now snapshots every file in the checkout, including git-ignored files, before and after a full run. It fails on any new file. Verified by planting a stray `.sqlite` file, which was detected.

**Cleanup**

- The test data folder at `%LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Local\OpenFilmStudio` was inspected read-only first:
  - created 16:49:26 by server PID 33464, which was Claude's test run
  - a second start at 16:50:46 (PID 34392), also Claude's test run
  - last activity at 16:50:52
  - the only setting was `ui.welcome_dismissed`, from Claude's test click
  - `media/` and `backups/` empty, and no tables capable of holding user content
- Confirmed as created only by M1 testing, so it was deleted by its explicit path. No other `OpenFilmStudio` data folder exists on the machine.
- Claude's scratchpad test copies were also removed.

**Requirements assigned to milestones (D16)**

| Requirement | Milestone | Where it is specified |
|---|---|---|
| Data-directory lock | M1.5 | `MASTER_PLAN.md` |
| Safe storage across updates | M1.5 and M11 | `MASTER_PLAN.md`, `RELEASE.md`, `TESTING.md` |
| Safe storage across uninstall | M11 release gate | `MASTER_PLAN.md`, `RELEASE.md`, `TESTING.md` |
| Windows MSIX (mandatory release blocker if MSIX is selected) | M11 release gate | `ARCHITECTURE.md`, `RELEASE.md` |
| Cross-platform runtime verification | M11 release gate | `MASTER_PLAN.md`, `RELEASE.md`, `TESTING.md` |
| Browser-level E2E | M11 release gate | `MASTER_PLAN.md`, `RELEASE.md`, `TESTING.md` |

### Known gaps and risks

- **macOS and Linux runs** are not executed, only unit-tested via platform simulation. This is now an M11 release gate.
- **No Playwright browser E2E.** `TESTING.md` lists Playwright, but browser downloads aren't feasible on this network. E2E coverage is a stdlib HTTP smoke test plus manual browser checks with screenshots. This is now an M11 release gate.
- **Other local processes** running as the same user can call the API. That's out of the single-user threat model. A per-launch token is a candidate for M11.
- **MSIX virtualization.** Processes started from the Claude desktop app had their AppData writes redirected to its package `LocalCache`. This is a mandatory release blocker if MSIX is selected (`RELEASE.md`).
- **`npm audit`** still reports the dev-only minimatch advisory from M0. No runtime packages are affected.
- **No production CSP for the UI yet.** It will be added when the backend serves the built UI (packaging, M11). The API already sends a restrictive CSP.
- **No single-instance lock yet.** Two backends on the same data directory are prevented only by the port check. The data-directory lock is assigned to M1.5.

## M1.5 evidence (2026-11-07)

**Commit:** the M1.5 implementation and documentation are committed on top of `c937316` as a single commit, not pushed. The hash is in the final report; a commit can't contain its own hash.

**Design and evidence:** `docs/UPDATES.md` has the GitHub API contract (verified 2026-11-07) and the Sigstore-vs-Ed25519 evaluation. Decisions D17–D21 were accepted after the final review; D22 records the deferrals.

### Acceptance criteria

| Requirement | Status | Evidence |
|---|---|---|
| Non-blocking background checks | PASS | An asyncio task runs after startup, with the check in a worker thread. `test_startup_is_not_blocked_by_a_hanging_network` (hung fetch; health responds in under 3 s) and `test_offline_background_failure_never_breaks_the_app` |
| Stable releases only | PASS | Drafts, prereleases and SemVer pre-release tags are filtered out. Release-parsing tests; the demo showed `0.3.0-rc.1` ignored |
| Semantic version comparison | PASS | SemVer 2.0, including the semver.org §11 ordering example, build metadata, and invalid tags (a trailing-newline bug was found and fixed) |
| Notification: version, notes, size | PASS | Current and new version, plain-text notes, release date, and per-OS/arch asset size. Screenshot 02 |
| Update Now / Remind Me Later / Skip Version | PASS (honest label) | Snooze lasts 3 days. Skip hides only that version. The primary action reads **How to Update** because one-click is unsupported; it reads "Update Now" only when `one_click_supported` (tested) |
| Manual check; configurable checks | PASS | "Check for Updates" (throttled to once a minute after a success); auto-check toggle; `OPENFILM_UPDATE_CHECK=0` |
| Offline without blocking | PASS | Offline, timeout, HTTP errors, oversized responses and bad redirects are recorded and shown calmly. The app keeps working. The manual check is disabled while offline |
| No project data or keys sent | PASS | `test_request_is_fixed_anonymous_and_minimal`: fixed URL, three fixed headers, no body or cookies; secret environment values absent. No request before the first-run disclosure (D8/D20) |
| No download or execution without approval | PASS | Nothing downloads release assets. `POST /api/updates/install` always returns 409 and downloads nothing (API and E2E tests) |
| Platform-aware; packaged / git / docker distinguished | PASS | Detects git, docker, packaged and source installs. Commands differ for Windows, macOS and Linux. Screenshot 03 (a real git checkout) |
| Git and Docker instructions | PASS | Git: official-remote check, clean-tree check, fetch tags, checkout tag, restart (the launcher reinstalls when lockfiles change). Docker: keep the volume, never `down -v`, set the tag, pull and up |
| Verified packaged installation | NOT IMPLEMENTED (by rule) | No signed installers exist, so no supported, tested mechanism exists. One-click is disabled (D21) |
| Release integrity and authenticity | PASS (building blocks; fails closed) | Ed25519 manifest: valid, tampered, wrong key, untrusted key, malformed, wrong repo or product, version mismatch, downgrade, pre-release. Artifact size and SHA-256. No trusted key yet, so `NO_TRUSTED_KEYS` |
| Sigstore and Ed25519 evaluated | PASS | `docs/UPDATES.md` § Release authenticity; D18 |
| Malicious URLs, traversal, invalid manifests | PASS | 17 malicious-release cases, 4 redirect cases, 7 malicious-archive entries, tar links and traversal, zip bombs, hostile release URLs kept out of commands |
| Downgrade prevention | PASS | Never offers equal or older versions. The manifest rejects downgrades. Rollback only through restoring a verified backup |
| Cross-platform data-directory lock | PASS (Windows executed) | `msvcrt` / `flock`. Real two-process test: the second engine exits with code 3 and the DB hash is unchanged. A crashed holder doesn't block startup. A locked folder is never opened or migrated |
| Backup before migration; transactional migrations | PASS | Verified backup, then one transaction. Failing-migration rollback test. A real M1 to M1.5 upgrade took a verified backup |
| Update failure recovery | PASS | `python -m app.recovery list/restore`: needs the lock, verifies checksum and schema, needs explicit confirmation (`RESTORE` or `--yes`), keeps a safety copy, touches no other files |
| Data preservation verification | PASS | `app/integrity.py` fingerprint. Tests and a real cross-version cycle (below) showed media and settings files unchanged |
| No user-data deletion; confirmation before destructive actions | PASS | Updates and restores never delete user files. Backups are never pruned automatically |
| UI: notification, notes, versions, actions, settings, manual check, guidance, loading/offline/error states | PASS | 16 update-UI tests (19 including parameterised cases). Screenshots 01–04 |
| Tests offline with mocked network | PASS | Network is blocked in tests except loopback. All GitHub interactions are faked |

### Real cross-version verification

`c937316` (M1) was exported to a scratch folder; this repository's git state was not touched.

1. The M1 engine created a schema-2 data folder. A setting was saved and media files were added.
2. **The M1.5 engine opened it:** schema 3, a verified `pre-migrate-0002-to-0003` backup, the setting preserved, and media byte-identical.
3. A second M1.5 engine on the same folder was refused with exit 3.
4. **The old M1 engine** on the upgraded folder was refused with `DB_NEWER_SCHEMA`, and the data was not modified.
5. **Recovery restore** of the pre-migration backup succeeded, and a safety copy was kept.
6. **M1 ran again** with schema 2 and the setting intact.
7. Across the whole cycle, no user file was removed or modified; only 4 backup files were added.

### Checks

| Gate | Result |
|---|---|
| `bash scripts/check.sh` and `scripts\check.ps1` | ALL CHECKS PASSED |
| Backend pytest | **282 passed**: 186 new, 96 from M0/M1 (final review) |
| Frontend Vitest | **38 passed**: 19 new, 19 from before |
| ruff, ruff format, mypy `--strict` (60 files), ESLint, `tsc` (app and config), production build | Clean |
| E2E smoke (real servers, through the proxy) | **11/11**, including update status and the refused install |
| Clean install of a fresh copy (130 files) | `dev.sh --smoke`, then `check.sh`, passed. Lockfile stamps were written |
| Secret scan | 130 files, 0 findings. No private key material in the tree |
| `npm audit --omit=dev` | 0 vulnerabilities in runtime packages. The 10 moderate findings are the known dev-only minimatch advisory |
| `pip-audit` (Python runtime closure) | No known vulnerabilities |

**Per-file test counts**

- Backend: `test_update_version_releases` 44, `test_update_verify` 32, `test_update_service` 28, `test_update_github` 20, `test_update_install` 19, `test_update_api` 14, `test_datalock_recovery` 14, `test_server_process` 5 (+1), `test_dev_launcher` 1, `test_migrations` 11 (updated)
- Frontend: `UpdateCenter.test` 16 (19 cases), plus updated fakes

### Screenshots

In `docs/screenshots/m1.5/`:

- `01-first-run-disclosure.jpg`
- `02-update-available-release-notes.jpg`
- `03-git-update-guide.jpg`
- `04-settings-after-skip.jpg`

They use a fake v0.2.0 release served from a scratch script outside the repository, injected through the test seam. No real GitHub request was made.

### Spend and dependencies

- **Spend:** $0.00. No provider or GitHub API calls were made by the app.
- **New runtime dependency:** `cryptography` (Apache-2.0 OR BSD-3-Clause), with `cffi` (MIT-0) and `pycparser` (BSD-3-Clause).
- **Dev dependencies:** unchanged.

### Defects found and fixed during M1.5

1. **Trailing-newline bypass.** `re.match` with `$` accepted a trailing newline (for example `1.2.3\n` or `evil.zip\n`). All whole-string validators now use `fullmatch`; regression tests added.
2. **SQLite deadlock.** Found in the real browser: React StrictMode's concurrent first requests failed with "database is locked". Fixed with `BEGIN IMMEDIATE`, by creating the state row in the migration (reads never write), and by never holding a DB transaction during the network call. A regression test fails without the fix (6 lock errors).
3. **Zip entries with bare permission bits** were wrongly rejected. Fixed.
4. **Launcher reinstall.** It only installed dependencies on first run, so after a git update stale dependencies would remain. It now reinstalls whenever a lockfile hash changes.
5. **Layout.** The home cards shrank inside the new column. Fixed.

### Known gaps and risks

- **One-click installation is not implemented** (by rule, D21). Disk-full, health-check-failure and automatic app-folder rollback tests move to M11 with it.
- **No release key exists yet.** Verification fails closed. The M11 key ceremony must generate, store and pin it and set up CI signing. Losing the key would require a key rotation release.
- **Backups are never pruned.** The plan's "configurable number of backups" is deferred (D21); disk usage grows with each schema upgrade.
- **The app version was not bumped.** `__version__` and `package.json` are still `0.1.0` for both M1 and M1.5. The maintainer should set the version when tagging a release, because the updater compares it.
- **Live GitHub behavior is unverified.** The repository has no releases. Redirect handling and the `digest` format are undocumented (see `docs/UPDATES.md`).
- **Only Windows was executed.** macOS and Linux locking (`flock`) and the launchers are untested on real systems (M11 release gate).
- **Docker guidance is generic** until an official image exists (M11).

### Final review before acceptance (2026-11-07)

**Decisions D17–D21 were checked against the code and earlier decisions.**

- **One conflict found and fixed (D20 vs D8).** A manual "Check for Updates" click had marked the first-run disclosure as answered. Because automatic checks default to on, one click would silently enable daily checks. Now:
  - A manual check is a single request the user asked for.
  - Automatic checks run only after the disclosure is answered.
  - The background check re-verifies consent and the setting inside its own transaction.
  - Two regression tests were added. D8 itself is unchanged.
- **Stale labels corrected.** D10–D14 still read "pending review" although M1 was accepted; their status labels were updated. No decision content changed.
- **No other conflicts** with the local-first, security, update or release requirements:
  - The updater is the only outbound call besides the selected AI provider and package installs, as `CLAUDE.md` allows.
  - It needs disclosure and can be disabled.
  - It sends no user data, never installs anything, and touches no user files.

**Database safety (regression tests in `backend/tests/test_database_safety.py`).**

- **No network inside write transactions:** while the fetch runs, a zero-timeout writer can take `BEGIN IMMEDIATE`. Tested on the manual, automatic and HTTP API paths.
- **No deadlock:** 6 concurrent checkers and 4 readers all finish with no errors, and only one network request runs at a time. The background loop plus parallel API checks return only 200 responses. The earlier test reproduces the original "database is locked" failure without the fix.
- **Atomic migrations:** the failing-migration test leaves nothing applied, and the verified backup remains.
- **Lock across processes:** tested with real processes. The lock is released after app shutdown, after a normal exit without an explicit release, and after a hard kill.
- **Recovery fixes:**
  1. A restore over a **corrupt** database previously failed and so blocked recovery: the safety backup's integrity check failed, and SQLite cannot write into a damaged file. Now the damaged file is preserved byte for byte with a verified SHA-256. The restored database is built in a temporary file and swapped in atomically.
  2. Leftover journal files are moved next to the safety copy, never replayed onto the restored database and never deleted.
  3. If no safety copy can be made, the restore aborts and the database is byte-identical.

**Security sweep.**

- Secret scan: 131 files, 0 findings. No private keys or tokens in the tree; test signing keys are generated at runtime.
- **One outbound call site:** the fixed anonymous GitHub request.
- **One-click stays off:** it is never enabled, there are no download or install functions, `TRUSTED_RELEASE_KEYS` is empty, and `/api/updates/install` returns 409.
- **Destructive operations are all intentional:** truncating our own lock file, deleting recovery's own temp file, moving journals, and replacing the database only after a verified safety copy and an explicit `RESTORE` or `--yes`.

**Deferred to M11 as mandatory release gates (D22; `MASTER_PLAN` M11, `RELEASE.md` blockers 5–11, `TESTING.md`):**

1. Signed, verified packaged updates
2. Tested one-click installation for supported packaged formats
3. Safe rollback after failed installations
4. Configurable backup retention with safe defaults
5. Windows, macOS and Linux runtime verification
6. Real-browser automated E2E

**Final gates:**

| Gate | Result |
|---|---|
| Backend pytest | 282 passed |
| Frontend Vitest | 38 passed |
| ruff, mypy `--strict` (61 files), ESLint, `tsc`, production build | Clean |
| E2E smoke | 11/11 |
| Secret scan | 0 findings |
| `check.sh` and `check.ps1` | ALL CHECKS PASSED |
