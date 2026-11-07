# Architecture

Local browser UI (React/TS/Vite/Tailwind) -> localhost FastAPI -> SQLite (SQLAlchemy/Alembic) + local media filesystem -> provider adapter (mock or verified Google video). FFmpeg performs local post-processing. Use a durable SQLite-backed jobs table for MVP; add Redis/Celery only if measured needs justify it.

Modules: projects, assets, scenes, prompts, providers, jobs, continuity, voices, costs, timeline, export. Provider API key is used only in backend. UI never calls provider directly. Use structured schemas (Pydantic + TypeScript types), provider capability flags and migration versions. Local default binds to 127.0.0.1; no cloud telemetry by default. API is not public without opt-in secure deployment.

Repository target: `frontend/`, `backend/app/`, `backend/tests/`, `docs/`, `scripts/`, `.github/workflows/`, `examples/`.

Flow: user picks project -> scene resolves references -> prompt compiler -> capability validation -> price estimate/budget reservation -> explicit Generate click -> queue -> provider -> media download -> review -> approve take -> timeline -> FFmpeg export.
