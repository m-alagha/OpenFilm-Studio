import { vi } from "vitest";

import type { AppSettings, Health, SystemInfo, UpdateStatus } from "../api/types";

export const okHealth: Health = {
  status: "ok",
  app_version: "0.1.0",
  database: { status: "ok", code: null, message: null },
};

export const system: SystemInfo = {
  app_version: "0.1.0",
  schema_version: 2,
  supported_schema_version: 2,
  database_created_by_app_version: "0.1.0",
  data_dir: "C:\\Users\\alex\\AppData\\Local\\OpenFilmStudio",
  local_only: true,
  provider: { provider_id: "mock", model_id: "mock-video-v0", is_mock: true },
};

export function updateStatus(overrides: Partial<UpdateStatus> = {}): UpdateStatus {
  return {
    current_version: "0.1.0",
    auto_check_enabled: true,
    disclosure_acknowledged: true,
    disabled_by_environment: false,
    last_checked_at: null,
    last_check_status: "never",
    available: null,
    notify: false,
    install: {
      type: "git",
      os: "windows",
      one_click_supported: false,
      one_click_reason: "Automatic installation is turned off until OpenFilm Studio publishes signed installers.",
      steps: [],
      rollback_steps: [],
    },
    ...overrides,
  };
}

export const availableUpdate: UpdateStatus = updateStatus({
  last_check_status: "ok",
  last_checked_at: "2026-11-07T12:00:00Z",
  notify: true,
  available: {
    version: "0.2.0",
    name: "OpenFilm Studio v0.2.0",
    notes: "New timeline.\n<script>alert(1)</script>",
    published_at: "2026-11-01T10:00:00Z",
    release_url: "https://github.com/m-alagha/OpenFilm-Studio/releases/tag/v0.2.0",
    download_size: 52428800,
    skipped: false,
    snoozed_until: null,
  },
  install: {
    type: "git",
    os: "windows",
    one_click_supported: false,
    one_click_reason: "Automatic installation is turned off until OpenFilm Studio publishes signed installers.",
    steps: [
      { title: "Stop OpenFilm Studio", detail: "Press Ctrl+C.", command: null },
      { title: "Switch to version 0.2.0", detail: "", command: "git checkout v0.2.0" },
    ],
    rollback_steps: [{ title: "Go back to your previous version", detail: "", command: "git checkout v0.1.0" }],
  },
});

export function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

type Handler = (url: string, init: RequestInit) => Response | Promise<Response>;

/** Installs a fetch mock routing by "METHOD /path". Unrouted requests reject. */
export function fakeBackend(routes: Record<string, Handler>) {
  const mock = vi.fn(async (input: RequestInfo | URL, init: RequestInit = {}) => {
    const url = String(input);
    const key = `${init.method ?? "GET"} ${url}`;
    const handler = routes[key];
    if (!handler) throw new TypeError(`Failed to fetch (${key})`);
    return handler(url, init);
  });
  vi.stubGlobal("fetch", mock);
  return mock;
}

export function readyBackend(settings: AppSettings = { "ui.welcome_dismissed": false }) {
  return fakeBackend({
    "GET /api/health": () => json(okHealth),
    "GET /api/system": () => json(system),
    "GET /api/settings": () => json(settings),
    "GET /api/updates": () => json(updateStatus()),
  });
}
