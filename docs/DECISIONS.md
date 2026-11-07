# Decision log

| ID | Date | Decision | Status |
|---|---|---|---|
| D1 | 2026-11-07 | **License: Apache-2.0.** `LICENSE` holds the official text from apache.org (sha256 `cfc7749b…3d30`). | ACCEPTED 2026-11-07 by the maintainer. It covers only original code and docs the maintainer owns or may license. Third-party dependencies and materials keep their own licenses; the audit is in `docs/THIRD_PARTY_NOTICES.md`. The trademark check for the project name is still open (see `docs/RELEASE.md`). |
| D2 | 2026-11-07 | **Toolchain** | ACCEPTED for M0 |
| D3 | 2026-11-07 | **Video provider target for M5: `gemini-omni-1.2-flash` via the Gemini Developer API (Interactions API)**. Evidence is in `PROVIDER_CAPABILITIES.md`. The Enterprise platform (Vertex AI) and Veo GA models are out of scope until verified. | ACCEPTED 2026-11-07 as the **provisional** primary provider. At M5, before any implementation, verify the raw API docs, actual request and response schemas, model availability and pricing. No paid request without the maintainer's explicit permission. |
| D4 | 2026-11-07 | **No runtime dependencies at M0.** The provider contract uses stdlib dataclasses. Pydantic and FastAPI arrive with M1 and M4, when there is an API boundary to validate. | ACCEPTED for M0 |
| D5 | 2026-11-07 | **Mock output is a JSON placeholder (`*.mock.json`), not a fake MP4**, so it cannot be mistaken for generated media. | ACCEPTED for M0 |
| D6 | 2026-11-07 | **API keys go in the `x-goog-api-key` header, never the `?key=` query parameter**, even though most Google Omni examples use the query parameter. This keeps keys out of URLs and logs. | ACCEPTED |
| D7 | 2026-11-07 | **In-app update manager is milestone M1.5**, between M1 and M2. It needs M1's app shell, settings and Alembic. It must exist before M2 creates real user data, so data separation, backups and rollback are in place from the start. Existing milestone numbers are unchanged. | ACCEPTED (maintainer request) |
| D8 | 2026-11-07 | **Update checks are on by default, but only after the first-run onboarding step discloses them.** The user can disable them in Settings, and `OPENFILM_UPDATE_CHECK=0` disables them too. A check sends only an anonymous request for public release metadata. | ACCEPTED 2026-11-07 by the maintainer: enabled by default after a transparent first-run disclosure, with an easy opt-out |
| D9 | 2026-11-07 | **The signing method for update artifacts is not chosen yet.** Candidates: Sigstore / GitHub artifact attestations, or minisign. It will be verified against official docs at M1.5 and published by M11. Until a signature can be verified, one-click archive install stays disabled and only instructions are offered. | ACCEPTED 2026-11-07: evaluate **Sigstore** and **Ed25519** signatures at M1.5. One-click updates stay disabled until release signatures can be verified |
| D10 | 2026-11-07 | **Windows data directory is `%LOCALAPPDATA%\OpenFilmStudio`, not roaming `%APPDATA%`**, so large media never syncs through roaming profiles. macOS: `~/Library/Application Support/OpenFilmStudio`. Linux: `$XDG_DATA_HOME/openfilm-studio` (absolute only), else `~/.local/share/openfilm-studio`. | ACCEPTED (maintainer, with M1) |
| D11 | 2026-11-07 | **Database compatibility is decided by schema version** (Alembic revision plus `app_meta.schema_version`), not app version. Newer, unknown or foreign databases are refused read-only. Migrations are forward-only, run in one transaction, and are preceded by a verified backup. | ACCEPTED (maintainer, with M1) |
| D12 | 2026-11-07 | **One-command dev start** is `scripts/dev.sh` or `scripts\dev.cmd`, wrapping the stdlib-only `scripts/dev.py`. Vite runs through `node` directly rather than the npm shim, so shutdown leaves no orphaned processes on Windows. `.cmd` instead of `.ps1` avoids the PowerShell execution policy. | ACCEPTED (maintainer, with M1) |
| D13 | 2026-11-07 | **No CORS.** The UI reaches the API same-origin, through the Vite proxy in development. Writes require the `X-OpenFilm-Client` header, and Host and Origin must be loopback. | ACCEPTED (maintainer, with M1) |
| D14 | 2026-11-07 | **`opentelemetry-api` is accepted as a FastAPI transitive dependency.** It is the no-op API with no SDK or exporter. A test forbids an SDK or exporter, and the server sets `OTEL_SDK_DISABLED=true`. | ACCEPTED (maintainer, with M1) |
| D15 | 2026-11-07 | **The official repository is `m-alagha/OpenFilm-Studio`** (https://github.com/m-alagha/OpenFilm-Studio). It is the only release source for the updater. Package metadata and docs point to it. Git history and remotes were not rewritten. | ACCEPTED (maintainer) |
| D16 | 2026-11-07 | **Release gates assigned to milestones.** The data-directory lock goes to M1.5. Safe storage across update and uninstall, Windows MSIX as a blocker, cross-platform runtime verification and browser-level E2E are M11 release gates (`docs/RELEASE.md`). | ACCEPTED (maintainer request) |
| D17 | 2026-11-07 | **GitHub Releases contract (verified 2026-11-07).** Use the list endpoint, not `/releases/latest` (which sorts by commit date), and pick the highest stable SemVer locally. Pin `X-GitHub-Api-Version: 2026-03-10`. Respect the 60 requests/hour unauthenticated limit and `retry-after` / `x-ratelimit-reset`. Evidence: `docs/UPDATES.md`. | ACCEPTED (maintainer, M1.5) |
| D18 | 2026-11-07 | **Release authenticity is an Ed25519-signed manifest** (`openfilm-release.json` + `.sig`), verified in the app with `cryptography` against pinned keys. Sigstore / GitHub artifact attestations are complementary CI provenance for M11, not an in-app requirement. No key is trusted yet, so verification fails closed. | ACCEPTED (maintainer, M1.5) |
| D19 | 2026-11-07 | **All SQLite transactions use `BEGIN IMMEDIATE`.** This was found in a real-browser test: concurrent read-then-write transactions deadlocked with "database is locked". Update checks never hold a DB transaction while waiting on the network. Recovery builds the restored database in a temporary file and swaps it in atomically. | ACCEPTED (maintainer, M1.5) |
| D20 | 2026-11-07 | **No automatic update request before the first-run disclosure is answered.** A manual "Check for Updates" click makes exactly one request that the user asked for. It does **not** answer the disclosure and never enables automatic checks. Automatic checks re-verify consent and the setting inside their own transaction. `OPENFILM_UPDATE_CHECK=0` disables all update network activity. *(Corrected in the final review: the first implementation treated a manual click as consent, which conflicted with D8.)* | ACCEPTED (maintainer, M1.5) |
| D21 | 2026-11-07 | **One-click install stays disabled.** No download or installer step is implemented. `POST /api/updates/install` always returns 409. The primary button reads "How to Update" until one-click is truly supported. Backups are never pruned automatically; configurable retention is deferred and will need confirmation. | ACCEPTED (maintainer, M1.5) |
| D22 | 2026-11-07 | **M1.5 items deferred to M11 as mandatory release gates** (maintainer instruction): signed, verified packaged updates; tested one-click installation for supported packaged formats; safe rollback after failed installations; configurable backup retention with safe defaults; Windows/macOS/Linux runtime verification; real-browser automated E2E. M1.5 does not implement them. | ACCEPTED (maintainer) |

## D2 toolchain details

**Backend**

- Python ≥ 3.11 (tested with 3.12), uv, and hatchling
- ruff for lint and format, mypy in strict mode, pytest

**Frontend**

- Node ≥ 22, npm
- TypeScript (strict), ESLint with typescript-eslint, Vitest
- React, Vite and Tailwind are deferred to M1.

**Checks**

- `scripts/check.sh` and `scripts/check.ps1` run everything.
- A stdlib secret scanner is used, because gitleaks is not installed in this environment and would add a binary dependency.
