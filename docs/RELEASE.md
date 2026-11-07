# Release and GitHub checklist

Choose and include verified license and third-party notices; confirm project name/trademark availability before publishing. README quick start and platform requirements; `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, issue/PR templates, changelog, security reporting contact, dependency lockfiles, CI tests, sample project with rights-cleared media, API key safety guide, screenshots, troubleshooting, backup/restore and uninstall. CI must run without paid credentials. Tag only after M11 acceptance.

## Release requirements for the in-app updater (M1.5 / M11)

- Releases are published only at the official repository, https://github.com/m-alagha/OpenFilm-Studio/releases. The updater trusts no other source.

- Use SemVer tags `vX.Y.Z`. Mark prereleases as GitHub prereleases. Stable releases must not be drafts.
- Release notes go in the release body.
- Each downloadable asset ships with a SHA-256 checksum file and a signature, using the method verified at M1.5.
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
