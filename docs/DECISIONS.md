# Decision log

| ID | Date | Decision | Status |
|---|---|---|---|
| D1 | 2026-11-07 | **License: Apache-2.0.** `LICENSE` holds the official text from apache.org (sha256 `cfc7749b…3d30`). | ACCEPTED 2026-11-07 by the maintainer. It covers only original code and docs the maintainer owns or may license. Third-party dependencies and materials keep their own licenses; the audit is in `docs/THIRD_PARTY_NOTICES.md`. The trademark check for the project name is still open (see `docs/RELEASE.md`). |
| D2 | 2026-11-07 | **Toolchain** | ACCEPTED for M0 |
| D3 | 2026-11-07 | **Video provider target for M5: `gemini-omni-1.2-flash` via the Gemini Developer API (Interactions API)**. Evidence is in `PROVIDER_CAPABILITIES.md`. The Enterprise platform (Vertex AI) and Veo GA models are out of scope until verified. | ACCEPTED 2026-11-07 as the **provisional** primary provider. At M5, before any implementation, verify the raw API docs, actual request and response schemas, model availability and pricing. No paid request without the maintainer's explicit permission. |
| D4 | 2026-11-07 | **No runtime dependencies at M0.** The provider contract uses stdlib dataclasses. Pydantic and FastAPI arrive with M1 and M4, when there is an API boundary to validate. | ACCEPTED for M0 |
| D5 | 2026-11-07 | **Mock output is a JSON placeholder (`*.mock.json`), not a fake MP4**, so it cannot be mistaken for generated media. | ACCEPTED for M0 |
| D6 | 2026-11-07 | **API keys go in the `x-goog-api-key` header, never the `?key=` query parameter**, even though most Google Omni examples use the query parameter. This keeps keys out of URLs and logs. | ACCEPTED |

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
