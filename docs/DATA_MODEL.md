# Data model (initial logical schema)

Project(id, name, type, description, settings, budget_usd, created_at)
Season(id, project_id, number, title)
Character(id, project_id, name, appearance_spec, default_outfit_id, voice_profile_id)
Outfit(id, character_id, name, spec)
Location(id, project_id, name, description, layout_spec)
Asset(id, project_id, owner_type, owner_id, media_type, relative_path, sha256, source, rights, created_at)
VoiceProfile(id, project_id, name, provider, provider_voice_id, language, accent, consent_status)
Scene(id, project_id, season_id nullable, title, sequence, script, location_id, status)
Shot(id, scene_id, sequence, prompt, duration_s, camera, reference_asset_ids, status)
ShotCharacter(shot_id, character_id, outfit_id nullable, role)
DialogueLine(id, shot_id, character_id, text, emotion, sequence)
GenerationJob(id, shot_id, provider, model_id, request_hash, status, provider_job_id, estimated_usd, actual_usd nullable, error_code, timestamps)
Take(id, shot_id, job_id, video_asset_id, approved, review_notes)
UsageEntry(id, project_id, job_id, type, amount_usd, source, status, created_at)

Use foreign keys and cascading rules deliberately. Enforce project-scoped authorization at API boundaries even in local mode. Never store raw API keys in DB. Store asset paths relative to managed root and reject traversal/symlinks in import.

AppMeta(key, value): app_version, schema_version, install_type
UpdateState(id=1, auto_check_enabled, last_checked_at, latest_seen_version, skipped_version nullable, snoozed_until nullable)
DbBackup(id, created_at, from_schema, to_schema, relative_path, sha256, reason, verified)

Update-related state stores no credentials. Backups live under the user-data directory's `backups/`, never in the app directory.

**Implemented at M1 (schema version 2):**

- `app_meta(key, value)`: `schema_version`, `created_by_app_version`, `created_at`, `last_opened_app_version`, `last_opened_at`.
- `app_settings(key, value_json, updated_at)`: only registered, typed keys are accepted. The only key so far is `ui.welcome_dismissed`. Never credentials.
- Alembic's `alembic_version` table.

Migrations live in `backend/app/db/migrations/versions/`. Each one bumps `SCHEMA_VERSION` (tests enforce this).
