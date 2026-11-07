# OpenFilm Studio — AI implementation blueprint

Open-source, local-first filmmaking studio. Download from GitHub, configure an eligible video-provider API key, create separate film/series projects, and generate short scenes from reusable characters, places, voices and references.

**Important:** Model names, endpoints, prices, feature availability and billing balance access must be verified against official provider documentation during M0. Do not assume the previously discussed “Gemini Omni 1.2 Flash” model/API exists or is accessible. Use an adapter and a mock provider until verified. No API key guarantees video generation.

## Start here
1. Read `CLAUDE.md` and `docs/MASTER_PLAN.md`.
2. Paste `prompts/START_CLAUDE.md` into Claude Code from the repository root.
3. Implement **M0 only**, report evidence, and stop for approval.
4. Repeat with `prompts/NEXT_MILESTONE.md` after approval.

## Docs
`docs/ARCHITECTURE.md`, `docs/DATA_MODEL.md`, `docs/API_INTEGRATION.md`, `docs/AGENTS.md`, `docs/TESTING.md`, `docs/SECURITY.md`, `docs/MILESTONE_TRACKER.md`, `docs/UX_SPEC.md`, `docs/RELEASE.md`.

## Principles
Simple onboarding; local ownership; reproducible outputs; explicit provider capabilities; honest costs; no fabricated continuity guarantees; safe defaults; open-source-ready licensing.
