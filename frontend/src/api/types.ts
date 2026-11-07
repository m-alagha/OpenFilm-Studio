/** Mirrors backend/app/api/*.py response models. */

export interface Health {
  status: "ok" | "error";
  app_version: string;
  database: {
    status: "ok" | "incompatible";
    code: string | null;
    message: string | null;
  };
}

export interface SystemInfo {
  app_version: string;
  schema_version: number;
  supported_schema_version: number;
  database_created_by_app_version: string;
  data_dir: string;
  local_only: boolean;
  provider: {
    provider_id: string;
    model_id: string;
    is_mock: boolean;
  };
}

export interface AppSettings {
  "ui.welcome_dismissed": boolean;
}

/** Mirrors backend/app/api/updates.py. */
export interface UpdateStep {
  title: string;
  detail: string;
  /** Fixed command template (never built from release metadata). */
  command: string | null;
}

export type InstallType = "git" | "docker" | "packaged" | "source";

export type CheckStatus =
  | "never"
  | "ok"
  | "offline"
  | "timeout"
  | "rate_limited"
  | "http_error"
  | "too_large"
  | "bad_redirect"
  | "invalid_response";

export interface UpdateStatus {
  current_version: string;
  auto_check_enabled: boolean;
  disclosure_acknowledged: boolean;
  disabled_by_environment: boolean;
  last_checked_at: string | null;
  last_check_status: CheckStatus;
  available: {
    version: string;
    name: string;
    notes: string;
    published_at: string | null;
    release_url: string;
    download_size: number | null;
    skipped: boolean;
    snoozed_until: string | null;
  } | null;
  notify: boolean;
  install: {
    type: InstallType;
    os: "windows" | "macos" | "linux";
    one_click_supported: boolean;
    one_click_reason: string;
    steps: UpdateStep[];
    rollback_steps: UpdateStep[];
  };
}
