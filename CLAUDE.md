# Claude Code — Repository operating instructions

You are the implementation engineer for OpenFilm Studio. Read `README.md`, `docs/MASTER_PLAN.md`, `docs/ARCHITECTURE.md`, `docs/TESTING.md`, `docs/SECURITY.md`, `docs/MILESTONE_TRACKER.md`, and `.claude/skills/openfilm-development/SKILL.md` before modifying files.

## Mandatory Local-First Data Policy

All user data MUST be stored locally on the user's device
by default.

This includes:
- Projects, movies, series, and episodes
- Characters and their reference images
- Locations and environment references
- Voice profiles and audio files
- Scenes, scripts, and storyboards
- Generated videos and images
- Generation history and cost tracking
- All metadata (reference provenance, review notes, job records)
- Application settings

Technical requirements:
- Use local SQLite for application data.
- Use the local filesystem for media storage.
- No mandatory user accounts or cloud databases.
- Store API keys securely using the OS credential store.
- Never upload user data except the minimum inputs
  explicitly required for AI generation.
- Send those inputs only to the provider the user selected, and only after
  the user has seen what will be sent and explicitly authorized that request.
- Inform users before sending data to external APIs.
- Support local backup, export, and import.
- Never collect telemetry without explicit opt-in.
- All milestones MUST preserve this architecture.

The only permitted outbound connections are:
1. The user-selected AI provider, for an explicitly authorized request.
2. The update check against GitHub Releases. The user can disable it. It
   sends no user data (see the Update Safety Policy).
3. Package registries during developer install (`uv sync`, `npm ci`).

Any other outbound connection requires a documented decision and user approval.

## Mandatory Update Safety Policy

The in-app update manager (milestone M1.5) and every later milestone MUST
follow these rules:
- Never install an update without explicit user approval.
- Update checks never block startup, never fail when offline, and can be
  disabled.
- Update checks never transmit projects, media, settings, identifiers, or
  API keys.
- Application files and user data live in separate directories. An update
  replaces only application files.
- Back up the database before any migration, and verify the backup before
  migrating.
- Verify downloaded update artifacts (checksum and signature) before use.
- Keep the previous version and the backup, so a failed update can be
  rolled back.
- Every schema change ships as a tested, forward-only migration, with a
  backup-based rollback path.


## Non-negotiable rules
1. Implement **exactly one milestone** per run. Start at M0. Milestone order is M0, M1, **M1.5**, M2 … M11. Never start the next milestone without explicit user approval.
2. Before edits: inspect repository, git status, existing files, tests, and current milestone. Preserve unrelated changes.
3. Follow acceptance criteria; tests are mandatory. Show commands and results, not just claims.
4. Never hardcode model IDs, endpoint contracts, pricing or feature support from memory. Verify official Google docs and record dated links, evidence and uncertainty. If browsing unavailable, label as unverified and implement mock adapter.
5. Do not claim real video generation, voice locking, video-reference input, provider account balance, or billing hard limits without live evidence.
6. Do not ask for, print, log, commit, or send API keys to the chat. Keys remain server-side; redact logs.
7. Keep mock mode usable without credentials or paid calls. No real paid request without explicit user action and displayed estimate.
8. Implement local-first, cross-platform workflows. Keep data migrations and tests reproducible.
9. Use least complexity. Do not add agents, cloud infra, or paid dependencies prematurely.
10. Finish with a milestone report: files changed, commands/tests, screenshots if UI, known gaps, cost, security notes, next milestone; then STOP.

## Definition of done
All milestone criteria pass, no critical security failures, docs updated, tracker marked with truthful evidence, git diff reviewed. Do not silently change scope.
