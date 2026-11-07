# OpenFilm Studio

Open-source, local-first AI filmmaking studio. You download it from GitHub, optionally configure a video-provider API key, create separate film or series projects, and generate short scenes from reusable characters, places, voices and references. Your data stays on your machine.

**Official repository:** https://github.com/m-alagha/OpenFilm-Studio

> **Status: M1 (local app bootstrap), a developer preview.** There is a local web app with a working engine, database and status screen. Creating films comes in later milestones. A one-click installer for non-technical users is planned for the public release (M11); for now, setup needs the developer tools below. See `docs/MILESTONE_TRACKER.md`.

## Provider status (verified 2026-11-07, docs only)

Google documents **Gemini Omni 1.2 Flash** (`gemini-omni-1.2-flash`, Stable) on the Gemini Developer API. It is paid-tier only; there is no free tier for this model. Real generation is **not implemented** until M5, and it has not been live-tested. Some features are not available through the API: audio or voice input, voice locking, a provider balance API, and hard spend caps. Full evidence, sources and unknowns are in [`docs/PROVIDER_CAPABILITIES.md`](docs/PROVIDER_CAPABILITIES.md).

An API key does not guarantee video generation. The key needs a paid billing account, and access is subject to regional and policy limits.

## Requirements

- Git
- [uv](https://docs.astral.sh/uv/getting-started/installation/), which also provides Python ≥ 3.11 (tested with 3.12)
- [Node.js](https://nodejs.org) ≥ 22, which includes npm

No API key or account is needed. The demo provider runs offline at no cost.

## Start OpenFilm Studio (one command)

```bash
git clone https://github.com/m-alagha/OpenFilm-Studio.git
cd OpenFilm-Studio
```

macOS / Linux:

```bash
sh scripts/dev.sh
```

Windows (Command Prompt or PowerShell):

```bat
scripts\dev.cmd
```

**What the start script does**

1. Installs missing dependencies the first time (from the lockfiles).
2. Starts the engine (backend) and the app (UI). Both are reachable only from this computer.
3. Waits until both respond.
4. Opens **http://127.0.0.1:5173** in your browser.

Press **Ctrl+C** to stop. Useful options:

- `--no-browser`: don't open a browser.
- `--smoke`: start everything, check it works, then stop.

### Where your data is stored

Your data is kept **outside the app folder**, so updating or deleting the app never touches it.

| OS | Default data folder |
|---|---|
| Windows | `%LOCALAPPDATA%\OpenFilmStudio` (for example `C:\Users\you\AppData\Local\OpenFilmStudio`) |
| macOS | `~/Library/Application Support/OpenFilmStudio` |
| Linux | `$XDG_DATA_HOME/openfilm-studio`, or `~/.local/share/openfilm-studio` if `XDG_DATA_HOME` is not set |

The folder contains:

- `openfilm.sqlite`: the database
- `media/`: media files
- `backups/`: automatic, verified database backups taken before any upgrade
- `logs/`: logs, with keys redacted

The app shows the exact path on its home screen. To use another location, set `OPENFILM_DATA_DIR` to an absolute path outside the app folder; the app refuses folders inside the app or repository. To back up, copy the folder while the app is stopped.

### Settings (environment variables)

| Variable | Default | Purpose |
|---|---|---|
| `OPENFILM_DATA_DIR` | OS data folder | Where user data lives (absolute path, outside the app) |
| `OPENFILM_PORT` | `8765` | Engine (backend) port on 127.0.0.1 |
| `OPENFILM_UI_PORT` | `5173` | App (UI) port on 127.0.0.1 |
| `OPENFILM_HOST` | `127.0.0.1` | Bind address. Anything other than loopback is refused unless `OPENFILM_ALLOW_NON_LOOPBACK=1` (for isolated containers only; the API has no authentication) |

## Check everything (developers)

Install the dev dependencies first:

```bash
cd backend && uv sync --frozen --extra dev
```

```bash
cd frontend && npm ci
```

Then run the checks.

macOS/Linux:

```bash
bash scripts/check.sh
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\check.ps1
```

The check script runs, in order:

1. the secret scan
2. ruff, mypy and pytest on the backend, including real server-process tests
3. the mock smoke test
4. ESLint, the TypeScript check, Vitest and the production build on the frontend
5. an end-to-end smoke test of the real engine and UI, using a temporary data folder

It prints `ALL CHECKS PASSED` on success.

## Troubleshooting

| Problem | Fix |
|---|---|
| **`invalid peer certificate: UnknownIssuer`** (uv) | Your network inspects TLS. Tell uv to use the OS certificate store: set `UV_SYSTEM_CERTS=true` (PowerShell: `$env:UV_SYSTEM_CERTS="true"`), then run the start script again. |
| **"port 8765 (backend) is already in use"** | OpenFilm Studio is probably already running in another window. Close it, or pick another port with `OPENFILM_PORT` / `OPENFILM_UI_PORT`. |
| **"Can't reach the OpenFilm Studio engine"** in the browser | The engine stopped or is still starting. The page retries by itself. If it doesn't recover, stop the start script with Ctrl+C and run it again. Check `logs/` in your data folder. |
| **"Your data needs a newer version of OpenFilm Studio"** | The data folder was used by a newer version. Nothing was changed. Update OpenFilm Studio, or point `OPENFILM_DATA_DIR` at a different folder. |
| **"not an OpenFilm Studio database"** | `OPENFILM_DATA_DIR` points at a folder whose `openfilm.sqlite` belongs to something else. It was left untouched. Choose another folder. |
| **uv cannot use a Microsoft Store Python** | Run `uv python install 3.12`, or install Python from python.org. |
| **`uv` / `node` not found** | Install them from the links under Requirements, then open a new terminal. |
| **PowerShell blocks `check.ps1`** | Run it with `powershell -ExecutionPolicy Bypass -File scripts\check.ps1`. `dev.cmd` needs no policy change. |
| **Start over with empty data** | Stop the app and rename your data folder (don't delete it until you're sure). A fresh one is created on the next start. |

## Secrets and data

- Never commit `.env`. Only `.env.example`, which holds placeholders, is tracked. The secret scan fails if a `.env` file or a key-shaped value is tracked.
- The engine and the app listen on 127.0.0.1 only, with no CORS, a Host-header check against DNS rebinding, and a required client header on every write.
- From M5, API keys are stored in the OS credential store, used only by the local backend, and never sent to the browser or written to logs.
- All projects, characters, locations, voices, media, metadata and settings stay on your device, in your OS data folder, separate from the app files, so updates never touch them.
- The only data that leaves your device is the minimum input for a generation you explicitly authorize. Update checks (M1.5, which you can turn off) send no user data.

## Docs

`CLAUDE.md`, `docs/MASTER_PLAN.md`, `docs/PROVIDER_CAPABILITIES.md`, `docs/DECISIONS.md`, `docs/THIRD_PARTY_NOTICES.md`, `docs/ARCHITECTURE.md`, `docs/DATA_MODEL.md`, `docs/API_INTEGRATION.md`, `docs/AGENTS.md`, `docs/TESTING.md`, `docs/SECURITY.md`, `docs/MILESTONE_TRACKER.md`, `docs/UX_SPEC.md`, `docs/RELEASE.md`.

For AI-assisted development, paste `prompts/START_CLAUDE.md` into Claude Code (M0), then use `prompts/NEXT_MILESTONE.md` after each approval.

## Principles

- Simple onboarding
- Local ownership of your data
- Reproducible outputs
- Explicit provider capabilities
- Honest costs
- No fabricated continuity guarantees
- Safe defaults

## License

Apache-2.0 for original OpenFilm Studio code and docs (see `docs/DECISIONS.md` D1). Third-party dependencies keep their own licenses (see `docs/THIRD_PARTY_NOTICES.md`).
