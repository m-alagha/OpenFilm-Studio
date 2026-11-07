# Milestone tracker

Statuses: NOT_STARTED, IN_PROGRESS, BLOCKED, ACCEPTED. Only user approves ACCEPTED.

| Milestone | Status | Evidence | Approval |
|---|---|---|---|
| M0 | ACCEPTED | See "M0 evidence" below | Maintainer, 2026-11-07, with conditions D1 and D3 |
| M1 | NOT_STARTED | — | — |
| M2 | NOT_STARTED | — | — |
| M3 | NOT_STARTED | — | — |
| M4 | NOT_STARTED | — | — |
| M5 | NOT_STARTED | — | — |
| M6 | NOT_STARTED | — | — |
| M7 | NOT_STARTED | — | — |
| M8 | NOT_STARTED | — | — |
| M9 | NOT_STARTED | — | — |
| M10 | NOT_STARTED | — | — |
| M11 | NOT_STARTED | — | — |

After each milestone record commit, commands and pass counts, screenshots (if applicable), verified provider links, spend, blockers, and user approval. Never mark ACCEPTED just because code was written.

## M0 evidence (2026-11-07)

**Commit:** recorded below the tracker table once committed.

### Provider verification (docs only, no live calls)

`docs/PROVIDER_CAPABILITIES.md` has 9 official sources, all accessed 2026-11-07.

- `gemini-omni-1.2-flash` exists. Google labels it Stable on the Gemini Developer API (Interactions API).
- Paid tier only.
- Video output is about $0.07/s at 720p ($12 per 1M output tokens).
- Not available through the API:
  - audio or voice input, and voice locking
  - a balance API
  - hard spend caps
  - a documented cancel
- Request and response field names are MEDIUM confidence. Re-verify them at M5.

### Checks run

| Check | Command | Result |
|---|---|---|
| Secret scan | `python scripts/check_secrets.py` | 46 files, 0 findings |
| Backend lint | `ruff check . ../scripts` | All checks passed |
| Backend format | `ruff format --check . ../scripts` | 12 files already formatted |
| Backend types | `mypy` (strict) | no issues in 11 source files |
| Backend tests | `pytest` | **31 passed**, 0 failed. Network is blocked by an autouse fixture |
| Mock smoke test | `python -m app.smoke` | estimate $0 → submit → running 50% → succeeded → `*.mock.json`. MOCK SMOKE TEST PASSED |
| Frontend | `npm run check` (ESLint, `tsc --noEmit`, Vitest) | **5 passed** |
| All checks, bash | `bash scripts/check.sh` | ALL CHECKS PASSED |
| All checks, PowerShell | `scripts\check.ps1` | ALL CHECKS PASSED |

**Clean install:** the files git would ship (46) were copied to an empty directory. There, `uv sync --frozen --extra dev`, `npm ci` and `scripts/check.sh` all passed.

### Spend and screenshots

- **Spend:** $0.00. No provider API calls, and no API key was used or requested.
- **Screenshots:** none, because M0 has no UI.

### Known issues

- `npm audit` reports 10 moderate findings. All come from one advisory, the minimatch ReDoS GHSA-g3hv-75wg-m249. It sits in the dev-only ESLint and typescript-eslint chain, which is not shipped. The only fix offered is downgrading ESLint to 9. Revisit at M11.
- Python 3.11 on this machine is a Microsoft Store alias that uv cannot use, so testing used Python 3.12.
- This machine's network inspects TLS, so uv needs `--native-tls`. This is documented in the README troubleshooting section.

### Approval (2026-11-07)

The maintainer approved M0 with these conditions:

1. **License (D1):** Apache-2.0 applies to original code and docs the maintainer owns or may license. A third-party license audit was added in `docs/THIRD_PARTY_NOTICES.md`: no runtime dependencies; dev dependencies are MIT, BSD, ISC, Apache-2.0, PSF-2.0, BlueOak-1.0.0 and MPL-2.0, all compatible.
2. **Provider (D3):** `gemini-omni-1.2-flash` via the Gemini Developer API is the **provisional** M5 target. M5 must re-verify the raw docs, schemas, availability and pricing first. No paid request without explicit permission.

All checks were re-run before the M0 commit and passed.
