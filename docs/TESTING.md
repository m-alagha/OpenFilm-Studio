# Testing and acceptance policy

Backend: pytest, FastAPI TestClient, schema/migration tests, provider mock contract tests. Frontend: Vitest + React Testing Library, Playwright happy-path e2e. Tooling: ruff, mypy where useful, ESLint, TypeScript check, secret scanning. FFmpeg export tests on generated fixtures.

Required checks per milestone: unit tests, integration tests, user flow, failure paths, data isolation, no leaked keys, zero real provider cost unless explicitly approved. Test permission failures, missing API key, offline mode, rate limits, retries, invalid uploads, unsafe paths, partial downloads, crashes and restarts. Verify cost ledger never double-counts duplicate retries and blocks new jobs on reserved budget. Include exact command output in reports.

Each milestone report must contain: scope, commits/diff, tests run/pass/fail, manual verification, screenshots when UI, blockers, unsupported capabilities, API charges incurred, security review, and STOP for approval.
