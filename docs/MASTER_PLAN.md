# Master implementation plan

## Product goal
An open-source local-first film studio where each film/series has its own character library, location library, voice assignments, scripts, scenes, references, generated takes, timeline, exports and usage budget. Easy GitHub install; configure eligible provider API credentials locally; no mandatory account or hosted backend.

## Milestone protocol
One milestone at a time. Each has deliverables, tests, acceptance gate. Stop after each. Do not skip. Use mock provider until real provider integration is verified.

### M0 — Provider feasibility and repository foundation
- Verify actual official Google video model/product/API names, availability, required billing/allowlisting, input/output constraints, reference image/video support, duration/resolution, pricing and usage/balance APIs. Record URL, access date and confidence in `docs/PROVIDER_CAPABILITIES.md`.
- If the named model is not officially documented or accessible, explicitly say so; select a verified compatible Google video model only with user approval. Never invent endpoints.
- Scaffold repo, license choice decision (Apache-2.0 proposed, confirm rights), gitignore, Python/Node toolchain, lint/test scripts, README and env example.
- Acceptance: official evidence matrix or clearly blocked items; mock smoke test; clean install steps; no secrets in git.

### M1 — Local app bootstrap and one-command startup
- React/TypeScript/Vite + Tailwind frontend; FastAPI backend; SQLite with Alembic; media directories; start script for macOS/Linux/Windows instructions; health endpoints.
- Acceptance: fresh clone -> documented setup -> browser opens; automated backend/frontend smoke tests; no API key needed for mock.

### M2 — Projects and asset library
- CRUD projects (film/series, seasons optional), scoped characters, locations, props, outfits, voice profiles; image uploads and reference metadata; import/export safe project bundle.
- Acceptance: two projects have isolated assets; upload validation; round-trip export/import tests.

### M3 — Scene editor and @mentions
- Scenes with ordered shots, character/location selectors, @mentions autocomplete, dialogue with speaker assignment, actions, camera, aspect ratio, duration and reference selectors; autosave and validation.
- Acceptance: scene drafts persist, references resolve only inside project, missing references flagged.

### M4 — Provider adapter and generation queue (mock-first)
- Typed provider interface: capabilities, validate_config, estimate, submit, poll, download, cancel-if-supported. Local job queue, retries/backoff, cancellation semantics, progress and result history.
- Acceptance: mock generation end-to-end; retry/idempotency tests; no duplicate charges on frontend retries.

### M5 — Verified Google video integration
- Implement **only officially supported** Google provider API operations discovered at M0. Secure credential setup, capability-aware UI, paid-call confirmation, polling and artifact storage. Handle quota, permissions and provider errors.
- Acceptance: mocked integration contract tests; opt-in live smoke test using user's own key; document unsupported features. If access blocked, milestone remains blocked, not faked.

### M6 — Continuity and reference workflow
- Character reference sets, location views, last-frame extraction, shot-to-shot handoff, optional prior-video reference only if provider supports it, continuity checklist and manual approval. Automatic checks can flag drift but never guarantee identity.
- Acceptance: reference provenance tracked, unsupported modes disabled, two-scene mock workflow and review screen tested.

### M7 — Voice and dialogue pipeline
- Per-character voice identity metadata; optional pluggable licensed TTS provider, uploaded audio, dialogue timing, voice previews, subtitle generation and lip-sync integration only where verified/authorized. Consent safeguards for cloned voices.
- Acceptance: stable mapping of speaker to voice asset; mock audio pipeline; clear unsupported paths; no unauthorized cloning.

### M8 — Cost center and budget guardrails
- Provider price catalog with verified date/version; estimated vs actual usage ledger, per-project budget, pending-job reservations, cost breakdown, warnings and user-controlled spending caps. Provider account balance only if official API exposes it; otherwise show 'unavailable', never pretend.
- Acceptance: unit tests for estimates, retries, cancellations, concurrency, budget cap and missing billing data; no paid job when app budget exceeded.

### M9 — Timeline, editing and export
- Shot ordering, multiple takes, trim, transitions, captions, soundtrack rights notices, FFmpeg assembly and export MP4 with metadata.
- Acceptance: deterministic sample film exported offline, audio sync and format checks.

### M10 — AI director assistants (optional)
- Prompt compiler, script-to-shot suggestion, scene review, drift detection heuristics, agent approvals and provenance. Agents never autonomously spend money or alter approved assets without confirmation.
- Acceptance: deterministic prompt assembly, review findings, explicit human approval gates.

### M11 — Open-source release and cross-platform hardening
- GitHub Actions CI, security scan, docs, contributor guide, issue templates, demo assets with clear rights, Docker optional, release checklist, sample mock project, backup/restore.
- Acceptance: clean machine onboarding, passing CI, secrets scan, license audit, reproducible demo, tagged release candidate.

## Out of scope for V1
Guaranteed face/voice identity, feature claims without provider support, automatic cloud billing enforcement, unlimited free generation, distributed multiuser hosting, autonomous paid generation.
