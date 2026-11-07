# UX specification

First run: welcome -> provider choice -> optional API key validation -> mock demo -> project creation. A user should be able to explore without credentials.

Sidebar: Projects, Characters, Locations, Voices, Scenes, Timeline, Usage, Settings. Each project is isolated. Scene editor: `@` mention autocomplete for project characters and locations; dialogue speaker picker, action, camera, mood, duration, references (images, last frame, previous take if supported), cost estimate and explicit Generate button. Show queued/running/failed/ready statuses and compare takes. Show warnings for unavailable provider capabilities.

Usage: app budget, reserved, estimated, actual, and provider account balance only if retrievable. Label mock estimates and unknowns. Avoid promising 'one click' when API entitlement or payment setup is required. Support RTL Arabic and English eventually, but do not block core MVP on localization.

## Updates (M1.5)

**First run**
- Onboarding includes an "Check for updates automatically" step. It explains that only public release information is requested, and that no projects or keys are sent.

**Notification**
- The notification is non-modal. It shows the new version, the current version, sanitized release notes, and the download size when known.
- Actions:
  - **Update Now**
  - **Remind Me Later** (snooze)
  - **Skip Version** (a newer version shows again)

**During an update**
- Steps are shown in order: download, verify, back up, install, migrate, health check.
- On failure, the user sees a clear rollback result and recovery steps.

**Git and Docker installs**
- **Update Now** opens copyable, installation-specific instructions instead of installing.

**Settings → Updates**
- Toggle for automatic checks, a "Check now" button, the last-checked time, the current version and the install type.
