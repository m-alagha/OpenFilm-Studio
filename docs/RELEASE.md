# Release and GitHub checklist

Choose and include verified license and third-party notices; confirm project name/trademark availability before publishing. README quick start and platform requirements; `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, issue/PR templates, changelog, security reporting contact, dependency lockfiles, CI tests, sample project with rights-cleared media, API key safety guide, screenshots, troubleshooting, backup/restore and uninstall. CI must run without paid credentials. Tag only after M11 acceptance.

## Release requirements for the in-app updater (M1.5 / M11)

- Releases are published only at the official repository, https://github.com/m-alagha/OpenFilm-Studio/releases. The updater trusts no other source.

- Use SemVer tags `vX.Y.Z`. Mark prereleases as GitHub prereleases. Stable releases must not be drafts.
- Release notes go in the release body.
- Each release publishes `openfilm-release.json` (asset names, platforms, SHA-256 and sizes) and `openfilm-release.json.sig` (an Ed25519 signature by the pinned release key). The format is in `docs/UPDATES.md`.
- Generate GitHub artifact attestations (Sigstore) in CI as additional provenance.
- Name platform assets `OpenFilm-Studio-<version>-<os>-<arch>.<zip|tar.gz>`, with os in `windows`, `macos` or `linux` and arch in `x64` or `arm64`.
- Document the update procedure per install type: git, Docker and archive.
- Before tagging, run the upgrade test from the previous release with a fixture user-data directory.

## Release blockers (mandatory; a release cannot be tagged until all pass)

1. **Data outside the app.** Every install type keeps persistent user data outside the application directory, git checkout, container image and installer-managed folders.
2. **Updates preserve data.** An update preserves the user-data directory and OS credentials. Only verified, backed-up migrations may change the DB.
3. **Uninstall preserves data.** Uninstalling never deletes user data by default. Removing it needs a separate, explicit, confirmed action. Reinstalling finds the existing data.
4. **Windows MSIX.** If MSIX packaging is chosen, the release is blocked until tests prove that data does not land in the package's virtualized `%LOCALAPPDATA%\Packages\<package>\LocalCache`, and that it survives uninstall. MSIX redirects AppData writes for packaged processes and deletes that folder on uninstall, as observed at M1. Without that proof, use a non-MSIX installer.
5. **Single instance per data directory.** The data-directory lock (M1.5) is verified on all three OSes.
6. **Cross-platform runtime verification.** The full checks, launcher smoke and update/rollback tests pass in CI on Windows, macOS and Linux.
7. **Browser-level E2E.** Real-browser tests pass on all three OSes (see `docs/TESTING.md`).
8. **Signed, verified packaged updates** (deferred from M1.5, D22):
   - The release key exists, held offline or in CI secrets and never in the repository.
   - Its public key is pinned in `TRUSTED_RELEASE_KEYS`.
   - Every release publishes a signed `openfilm-release.json`.
9. **Tested one-click installation** for each supported packaged format: verify, extract safely, install side by side, health check, switch. Until then, one-click stays disabled.
10. **Safe rollback after a failed installation:** automatic restore of the previous app version and the pre-migration backup. Tested for failure at every step.
11. **Configurable backup retention with safe defaults.** It never removes the newest verified backups, and prunes only with confirmation.
