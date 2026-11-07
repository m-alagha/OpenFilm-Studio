# Release and GitHub checklist

Choose and include verified license and third-party notices; confirm project name/trademark availability before publishing. README quick start and platform requirements; `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, issue/PR templates, changelog, security reporting contact, dependency lockfiles, CI tests, sample project with rights-cleared media, API key safety guide, screenshots, troubleshooting, backup/restore and uninstall. CI must run without paid credentials. Tag only after M11 acceptance.

## Release requirements for the in-app updater (M1.5 / M11)

- Use SemVer tags `vX.Y.Z`. Mark prereleases as GitHub prereleases. Stable releases must not be drafts.
- Release notes go in the release body.
- Each downloadable asset ships with a SHA-256 checksum file and a signature, using the method verified at M1.5.
- Document the update procedure per install type: git, Docker and archive.
- Before tagging, run the upgrade test from the previous release with a fixture user-data directory.
