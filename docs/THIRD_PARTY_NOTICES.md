# Third-party license audit

**Audited:** 2026-11-07, at M0. Package licenses were read from installed package metadata and from `frontend/package-lock.json`.

## Scope of the project license

- **Apache-2.0** applies only to the original OpenFilm Studio code and docs, which the maintainer owns or has the right to license.
- It does **not** relicense third-party dependencies, copied materials or assets. Those keep their own licenses.

## Runtime dependencies

None. At M0 the backend has `dependencies = []` and the frontend has no `dependencies`. Nothing third-party ships with the app.

## Development-only dependencies

These are installed locally for linting and testing. They are not redistributed in this repository; only lockfiles that reference them are committed.

| Ecosystem | Licenses found | Packages | Compatible with an Apache-2.0 project? |
|---|---|---|---|
| Python (`backend/uv.lock`, 13 packages) | MIT, BSD-2-Clause, BSD (colorama), Apache-2.0 OR BSD-2-Clause (packaging), PSF-2.0 (typing_extensions), **MPL-2.0 (pathspec)** | pytest, ruff, mypy and their dependencies | Yes |
| npm (`frontend/package-lock.json`, 152 packages, all `dev`) | MIT 110, Apache-2.0 15, BSD-2/3-Clause 8, ISC 6, **MPL-2.0 12** (lightningcss and platform binaries, pulled in through vitest), **BlueOak-1.0.0 1** (minimatch) | typescript, eslint, typescript-eslint, vitest and their dependencies | Yes |

**About MPL-2.0:** it is file-level weak copyleft. It only matters if those files are modified or redistributed, and here they are used unmodified as separate tool dependencies. **Re-audit if any MPL package becomes a runtime or bundled dependency.** BlueOak-1.0.0 and PSF-2.0 are permissive.

## Copied materials and assets

| Item | Origin | License or status |
|---|---|---|
| `LICENSE` | Official Apache License 2.0 text from https://www.apache.org/licenses/LICENSE-2.0.txt (sha256 `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`) | Apache's license text, meant to be included verbatim |
| `docs/PROVIDER_CAPABILITIES.md` | Facts paraphrased from Google documentation, with links. Only API identifiers (model IDs, field names) are reproduced | No Google text or images copied |
| Images, video, audio, fonts | None in the repository | n/a |

## Re-audit triggers

Each later milestone must update this file when it:

- adds a runtime dependency (such as FastAPI or React),
- bundles a frontend build, or
- adds sample or demo media.

M11 runs a full license audit before release.
