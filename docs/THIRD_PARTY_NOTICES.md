# Third-party license audit

**Audited:** 2026-11-07 at M0, and re-audited at M1 when the first runtime dependencies were added. Package licenses were read from installed package metadata and from `frontend/package-lock.json`.

## Scope of the project license

- **Apache-2.0** applies only to the original OpenFilm Studio code and docs, which the maintainer owns or has the right to license.
- It does **not** relicense third-party dependencies, copied materials or assets. Those keep their own licenses.

## Runtime dependencies (re-audited at M1, 2026-11-07)

**Backend runtime closure** (`uv export --no-dev`, 18 packages at M1, plus 3 at M1.5):

| Packages | License |
|---|---|
| fastapi, pydantic, pydantic-core, SQLAlchemy, alembic, Mako, anyio, h11, annotated-types, annotated-doc, typing-inspection | MIT |
| starlette, uvicorn, click, idna, MarkupSafe | BSD-3-Clause |
| opentelemetry-api (required by FastAPI) | Apache-2.0 |
| typing_extensions | PSF-2.0 |
| cryptography (added M1.5, Ed25519 release verification) | Apache-2.0 OR BSD-3-Clause |
| cffi (via cryptography) | MIT-0 |
| pycparser (via cffi) | BSD-3-Clause |
| colorama (Windows only, via click) | BSD-3-Clause |

**About `opentelemetry-api`:** it is the no-op tracing API. Without an SDK and exporter it cannot send anything. A test (`test_no_opentelemetry_sdk_or_exporter_installed`) fails if an SDK or exporter is ever installed, and the server sets `OTEL_SDK_DISABLED=true`. There is no telemetry.

**Frontend runtime bundle** (non-dev npm packages): react, react-dom and scheduler, all MIT.

All runtime licenses are permissive and compatible with Apache-2.0. Before the release audit at M11, a NOTICE file listing these packages and their licenses must ship with distributed builds.

## Development and build-only dependencies

These are installed locally for linting, testing and building. They are not shipped in the app bundle; only lockfiles that reference them are committed.

| Ecosystem | Licenses found | Compatible? |
|---|---|---|
| Python dev extra | pytest, ruff, mypy, httpx2 and their dependencies. Licenses: MIT, BSD-2/3-Clause, Apache-2.0 OR BSD-2-Clause, **MPL-2.0 (pathspec)** | Yes |
| npm (`frontend/package-lock.json`, 284 packages; all but 3 are dev) | MIT 223, Apache-2.0 18, ISC 13, BSD-2/3-Clause 11, **MPL-2.0 12** (lightningcss, via Vite and Tailwind), BlueOak-1.0.0 2, MIT-0 2, 0BSD 1, CC0-1.0 1 (mdn-data), **CC-BY-4.0 1 (caniuse-lite)** | Yes |

**About MPL-2.0:** it is file-level weak copyleft. The packages are used unmodified as build tools, and their files do not end up in the bundle.

**About CC-BY-4.0:** `caniuse-lite` is browser-support data that the build reads at build time. It is not bundled. Attribution would be required only if it were redistributed.

**Re-audit** whenever a dependency moves into the runtime set.

## Copied materials and assets

| Item | Origin | License or status |
|---|---|---|
| `LICENSE` | Official Apache License 2.0 text from https://www.apache.org/licenses/LICENSE-2.0.txt (sha256 `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`) | Apache's license text, meant to be included verbatim |
| `docs/PROVIDER_CAPABILITIES.md` | Facts paraphrased from Google documentation, with links. Only API identifiers (model IDs, field names) are reproduced | No Google text or images copied |
| `docs/screenshots/m1/*.jpg`, `docs/screenshots/m1.5/*.jpg` | Screenshots of this app, taken during M1 and M1.5 verification | Original project material |
| Third-party images, video, audio, fonts | None in the repository | n/a |

## Re-audit triggers

Each later milestone must update this file when it:

- adds a runtime dependency (such as FastAPI or React),
- bundles a frontend build, or
- adds sample or demo media.

M11 runs a full license audit before release.
