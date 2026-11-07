# Milestone tracker

Statuses: NOT_STARTED, IN_PROGRESS, BLOCKED, ACCEPTED. Only user approves ACCEPTED.

Order: M0 → M1 → M1.5 → M2 … M11. M1.5 was inserted on 2026-11-07 at the maintainer's request, without renumbering the other milestones.

| Milestone | Status | Evidence | Approval |
|---|---|---|---|
| M0 | ACCEPTED | See "M0 evidence" below | Maintainer, 2026-11-07, with conditions D1 and D3 |
| M1 | ACCEPTED | See "M1 evidence" below | Maintainer, 2026-11-07, after final checks (repository identity, local-first audit, cleanup) |
| M1.5 | NOT_STARTED (mandatory in-app update manager, added 2026-11-07) | — | — |
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
