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
| User-data directory: OS default (Windows `%APPDATA%\OpenFilmStudio`, macOS `~/Library/Application Support/OpenFilmStudio`, Linux `${XDG_DATA_HOME:-~/.local/share}/openfilm-studio`), or `OPENFILM_DATA_DIR` | `openfilm.sqlite`, `media/`, `settings`, `backups/`, `logs/` | Only by DB migrations, and only after a verified backup |
| OS credential store | API keys | Never |

The exact OS paths are confirmed at M1. The app never writes user data inside the app directory.

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
