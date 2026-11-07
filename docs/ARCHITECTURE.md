# Architecture

Local browser UI (React/TS/Vite/Tailwind) -> localhost FastAPI -> SQLite (SQLAlchemy/Alembic) + local media filesystem -> provider adapter (mock or verified Google video). FFmpeg performs local post-processing. Use a durable SQLite-backed jobs table for MVP; add Redis/Celery only if measured needs justify it.

Modules: projects, assets, scenes, prompts, providers, jobs, continuity, voices, costs, timeline, export, updates, backup. Provider API key is used only in backend. UI never calls provider directly. Use structured schemas (Pydantic + TypeScript types), provider capability flags and migration versions. Local default binds to 127.0.0.1; no cloud telemetry by default. API is not public without opt-in secure deployment.

Repository target: `frontend/`, `backend/app/`, `backend/tests/`, `docs/`, `scripts/`, `.github/workflows/`, `examples/`.

Flow: user picks project -> scene resolves references -> prompt compiler -> capability validation -> price estimate/budget reservation -> explicit Generate click -> queue -> provider -> media download -> review -> approve take -> timeline -> FFmpeg export.

## Local-first guarantees

1. **Stored locally by default.** All user data stays on the user's device unless the user explicitly exports it:
   - projects, films, series and episodes
   - characters, outfits and reference images
   - locations and environment references
   - voice profiles and audio
   - scenes, scripts and storyboards
   - generated video and images
   - all metadata: reference provenance, job records, review notes, generation history and cost ledger
   - application settings
2. **Storage.** Structured data lives in a local SQLite database. Media lives on the local filesystem under the user-data directory, with relative paths.
3. **Credentials.** API keys live only in the OS credential store. They are never kept in SQLite, settings files, exports, backups, logs or the browser.
4. **Minimum disclosure to providers.** A generation sends only the inputs it needs (prompt text and the selected references), and only to the provider the user selected. Before the request, the UI shows exactly which text and media will be sent, plus the cost estimate. Nothing is sent until the user explicitly authorizes it.
5. **No other egress.** No telemetry or analytics unless the user opts in. The permitted outbound connections are listed in `CLAUDE.md`. Tests block the network by default.
6. **The user controls their data.** Local backup, export, import and delete are provided. No account or cloud database is required.

## Application files vs. user data

| Location | Contents | Changed by updates? |
|---|---|---|
| App directory (git checkout, release archive dir, or container image) | Code, frontend build, migrations | Yes. Replaced as a whole version |
| User-data directory: OS default (Windows `%LOCALAPPDATA%\OpenFilmStudio`, macOS `~/Library/Application Support/OpenFilmStudio`, Linux `${XDG_DATA_HOME:-~/.local/share}/openfilm-studio`), or `OPENFILM_DATA_DIR` | `openfilm.sqlite`, `media/`, `settings`, `backups/`, `logs/` | Only by DB migrations, and only after a verified backup |
| OS credential store | API keys | Never |

Paths were confirmed at M1 (`backend/app/paths.py`).

- **Windows uses `LOCALAPPDATA`, not roaming `APPDATA`.** Media can be large and must not sync through roaming profiles.
- **Linux uses `XDG_DATA_HOME`** only when it is absolute, as the XDG spec requires.
- **The app never writes user data inside the app directory.** At startup it refuses a data directory located inside the app or repository.
- **MSIX caveat:** when OpenFilm Studio is started by an MSIX-packaged Windows app, Windows redirects AppData writes into that package's private `LocalCache`. Packaged-app uninstalls delete that folder. The M11 Windows installer must therefore not be an MSIX package that relies on AppData, or must use a non-virtualized location.

## Update manager (M1.5)

**Check flow**

1. A background task (`updates` module) runs after startup.
2. If checks are enabled, it makes an anonymous HTTPS GET to GitHub Releases for the configured repository, with a short timeout. The result is cached, and checks run at most about once a day.
3. It filters out drafts and prereleases.
4. It compares versions using SemVer.
5. It applies the user's skip and snooze state.
6. If a newer stable version is available, it emits a notification to the UI.

**Install flow:** on **Update Now**, the steps depend on the install type.

- **Archive install**
  1. Download to `staging/`.
  2. Verify the checksum and signature.
  3. Extract safely.
  4. Back up the DB (SQLite online backup, then checksum).
  5. Start the new version, run migrations, and run a health check.
  6. On success, switch to the new version. On failure, roll back: restore the previous app directory and the DB backup.
- **Git and Docker installs:** show verified, step-by-step instructions instead.

Nothing is installed without an explicit user action. The update check sends no user data.

## M1 implementation

### Backend layout (`backend/app/`)

| File or module | Role |
|---|---|
| `main.py` | App factory and lifespan: prepare the data directory, open the database |
| `__main__.py` | `python -m app`: loopback check, redacting logs, uvicorn |
| `config.py` | Settings from the environment; refuses non-loopback binding without explicit opt-in |
| `paths.py` | OS data directory and the inside-app guard |
| `security.py` | Host and Origin checks, client header on writes, security headers |
| `logging_setup.py` | Redacting log handlers |
| `db/` | `engine.py` (transactional SQLite), `models.py`, `migrate.py` (compatibility check, verified backup, upgrade), `backup.py`, `migrations/` (Alembic, forward-only) |
| `api/` | `/api/health`, `/api/system`, `/api/settings` |
| `providers/` | M0 contract and mock provider, unchanged |

### Database compatibility rules (`db/migrate.py`)

1. **Empty or missing database:** created at the head migration. `app_meta` records `schema_version`, `created_by_app_version`, `last_opened_app_version` and timestamps.
2. **Older database:** a verified backup is taken first (SQLite online backup, `PRAGMA integrity_check`, and a SHA-256 sidecar file in `backups/`). All pending migrations then run in one transaction; DDL is transactional through SQLAlchemy's pysqlite recipe. If the upgrade fails, nothing is applied and the backup remains.
3. **Database from a newer app** (unknown Alembic revision, or `schema_version` above what this app supports): refused. The file is opened read-only for inspection and is never modified. The engine stays up in a blocked state: `/api/health` returns 503 with code `DB_NEWER_SCHEMA`, and the UI explains what to do.
4. **Non-OpenFilm or corrupt SQLite file:** refused, never adopted (`DB_UNRECOGNIZED` or `DB_UNREADABLE`).

Compatibility is decided by schema version, not app version. A newer app that did not change the schema stays compatible.

### Local API security (threat: a web page in the user's browser calling `127.0.0.1`)

- **Loopback-only binding.** Any other address is refused unless explicitly opted in.
- **Host-header allowlist** of loopback names, against DNS rebinding.
- **Origin check:** an `Origin` header, when present, must be a loopback origin.
- **Writes need the `X-OpenFilm-Client` header.** Cross-site pages cannot send it without a CORS preflight, and CORS is not enabled.
- **Response headers:** `nosniff`, `DENY` framing, `no-referrer`, a restrictive CSP for API responses, and `no-store`. No `Server` header.
- **Same-origin UI.** In development, the UI reaches the API through Vite's same-origin proxy.

**Not covered:** other local processes running as the same user. That is out of scope for a single-user local app. A per-launch session token is a candidate for M11 packaging.
