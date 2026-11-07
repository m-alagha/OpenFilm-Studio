/**
 * The only way the UI talks to the backend: same-origin requests to /api on
 * the local machine. The UI never calls AI providers and never handles keys.
 */

import type { AppSettings, Health, SystemInfo, UpdateStatus } from "./types";

export const CLIENT_HEADER = "X-OpenFilm-Client";
export const REQUEST_TIMEOUT_MS = 8000;

export type ApiErrorKind = "unreachable" | "timeout" | "http";

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number | undefined;
  readonly code: string | undefined;

  constructor(kind: ApiErrorKind, message: string, status?: number, code?: string) {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
    this.status = status;
    this.code = code;
  }
}

interface RequestOptions {
  method?: "GET" | "PUT" | "POST";
  body?: unknown;
  /** HTTP statuses whose JSON body is a valid result rather than an error. */
  acceptStatuses?: number[];
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = options.method ?? "GET";
  const headers: Record<string, string> = { Accept: "application/json" };
  if (method !== "GET") {
    headers["Content-Type"] = "application/json";
    headers[CLIENT_HEADER] = "web";
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  let response: Response;
  try {
    response = await fetch(path, {
      method,
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      credentials: "same-origin",
      cache: "no-store",
      signal: controller.signal,
    });
  } catch {
    if (controller.signal.aborted) {
      throw new ApiError("timeout", "The OpenFilm Studio engine took too long to respond.");
    }
    throw new ApiError("unreachable", "Can't reach the OpenFilm Studio engine.");
  } finally {
    clearTimeout(timer);
  }

  if (response.ok || options.acceptStatuses?.includes(response.status)) {
    return (await response.json()) as T;
  }
  let code: string | undefined;
  let message = `Request failed (${response.status}).`;
  try {
    const body = (await response.json()) as { error?: { code?: string; message?: string } };
    code = body.error?.code;
    if (body.error?.message) message = body.error.message;
  } catch {
    // Non-JSON error body: keep the generic message.
  }
  throw new ApiError("http", message, response.status, code);
}

export const api = {
  health: () => request<Health>("/api/health", { acceptStatuses: [503] }),
  system: () => request<SystemInfo>("/api/system"),
  settings: () => request<AppSettings>("/api/settings"),
  setSetting: <K extends keyof AppSettings>(key: K, value: AppSettings[K]) =>
    request<AppSettings>(`/api/settings/${encodeURIComponent(key)}`, {
      method: "PUT",
      body: { value },
    }),
  updates: () => request<UpdateStatus>("/api/updates"),
  setUpdatePreferences: (prefs: { auto_check_enabled?: boolean; disclosure_acknowledged?: boolean }) =>
    request<UpdateStatus>("/api/updates/preferences", { method: "PUT", body: prefs }),
  checkForUpdates: () => request<UpdateStatus>("/api/updates/check", { method: "POST" }),
  snoozeUpdate: () => request<UpdateStatus>("/api/updates/snooze", { method: "POST" }),
  skipUpdate: (version: string) =>
    request<UpdateStatus>("/api/updates/skip", { method: "POST", body: { version } }),
};
