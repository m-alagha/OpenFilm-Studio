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
| D10 | 2026-11-07 | **Windows data directory is `%LOCALAPPDATA%\OpenFilmStudio`, not roaming `%APPDATA%`**, so large media never syncs through roaming profiles. macOS: `~/Library/Application Support/OpenFilmStudio`. Linux: `$XDG_DATA_HOME/openfilm-studio` (absolute only), else `~/.local/share/openfilm-studio`. | ACCEPTED for M1 (pending review) |
| D11 | 2026-11-07 | **Database compatibility is decided by schema version** (Alembic revision plus `app_meta.schema_version`), not app version. Newer, unknown or foreign databases are refused read-only. Migrations are forward-only, run in one transaction, and are preceded by a verified backup. | ACCEPTED for M1 (pending review) |
| D12 | 2026-11-07 | **One-command dev start** is `scripts/dev.sh` or `scripts\dev.cmd`, wrapping the stdlib-only `scripts/dev.py`. Vite runs through `node` directly rather than the npm shim, so shutdown leaves no orphaned processes on Windows. `.cmd` instead of `.ps1` avoids the PowerShell execution policy. | ACCEPTED for M1 (pending review) |
| D13 | 2026-11-07 | **No CORS.** The UI reaches the API same-origin, through the Vite proxy in development. Writes require the `X-OpenFilm-Client` header, and Host and Origin must be loopback. | ACCEPTED for M1 (pending review) |
| D14 | 2026-11-07 | **`opentelemetry-api` is accepted as a FastAPI transitive dependency.** It is the no-op API with no SDK or exporter. A test forbids an SDK or exporter, and the server sets `OTEL_SDK_DISABLED=true`. | ACCEPTED for M1 (pending review) |

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
