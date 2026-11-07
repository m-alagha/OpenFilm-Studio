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
