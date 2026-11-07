import { vi } from "vitest";

import type { AppSettings, Health, SystemInfo } from "../api/types";

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
  });
}
