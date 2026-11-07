# OpenFilm Studio

Open-source, local-first AI filmmaking studio. You download it from GitHub, optionally configure a video-provider API key, create separate film or series projects, and generate short scenes from reusable characters, places, voices and references. Your data stays on your machine.

> **Status: M0 (foundation).** There is no app UI yet. The repository contains the provider contract, an offline mock provider, the toolchain and the provider evidence matrix. See `docs/MILESTONE_TRACKER.md`.

## Provider status (verified 2026-11-07, docs only)

Google documents **Gemini Omni 1.2 Flash** (`gemini-omni-1.2-flash`, Stable) on the Gemini Developer API. It is paid-tier only; there is no free tier for this model. Real generation is **not implemented** until M5, and it has not been live-tested. Some features are not available through the API: audio or voice input, voice locking, a provider balance API, and hard spend caps. Full evidence, sources and unknowns are in [`docs/PROVIDER_CAPABILITIES.md`](docs/PROVIDER_CAPABILITIES.md).

An API key does not guarantee video generation. The key needs a paid billing account, and access is subject to regional and policy limits.

## Requirements

- Git
- Python ≥ 3.11 (tested with 3.12) and [uv](https://docs.astral.sh/uv/)
- Node.js ≥ 22 with npm

No API key is needed. The mock provider runs offline at no cost.

## Install

```bash
git clone <repo-url> OpenFilm-Studio
cd OpenFilm-Studio
cd backend && uv sync --frozen --extra dev && cd ..
cd frontend && npm ci && cd ..
```

## Check everything

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
2. ruff, mypy and pytest on the backend
3. the offline mock smoke test
4. ESLint, the TypeScript check and Vitest on the frontend

It prints `ALL CHECKS PASSED` on success.

Individual commands:

```bash
cd backend && uv run pytest              # backend tests (network is blocked inside tests)
cd backend && uv run python -m app.smoke # mock estimate -> submit -> poll -> download
python scripts/check_secrets.py          # scan git-tracked files for keys / .env files
cd frontend && npm run check             # lint + typecheck + tests
```

### Troubleshooting

- **`invalid peer certificate: UnknownIssuer` from uv**: your network inspects TLS. Add `--native-tls` so uv uses the OS certificate store, for example `uv sync --frozen --extra dev --native-tls`.
- **uv cannot use a Microsoft Store Python**: install Python from python.org, or run `uv python install 3.12`.

## Secrets and data

- Never commit `.env`. Only `.env.example`, which holds placeholders, is tracked. The secret scan fails if a `.env` file or a key-shaped value is tracked.
- From M5, API keys are stored in the OS credential store, used only by the local backend, and never sent to the browser or written to logs.
- All projects, characters, locations, voices, media, metadata and settings stay on your device. From M1 they live in your OS user-data directory, separate from the app files, so updates never touch them.
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
