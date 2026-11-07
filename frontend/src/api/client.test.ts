import { afterEach, describe, expect, it, vi } from "vitest";

import { fakeBackend, json, okHealth } from "../test/fakeBackend";
import { ApiError, CLIENT_HEADER, REQUEST_TIMEOUT_MS, api } from "./client";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("api client", () => {
  it("uses same-origin relative URLs and no client header for reads", async () => {
    const fetchMock = fakeBackend({ "GET /api/health": () => json(okHealth) });
    await api.health();
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/health");
    expect(init.credentials).toBe("same-origin");
    expect((init.headers as Record<string, string>)[CLIENT_HEADER]).toBeUndefined();
  });

  it("sends the client header and JSON body on writes", async () => {
    const fetchMock = fakeBackend({
      "PUT /api/settings/ui.welcome_dismissed": () => json({ "ui.welcome_dismissed": true }),
    });
    await api.setSetting("ui.welcome_dismissed", true);
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>)[CLIENT_HEADER]).toBe("web");
    expect(init.body).toBe('{"value":true}');
  });

  it("returns the health body for 503 (incompatible database)", async () => {
    const body = { ...okHealth, status: "error", database: { status: "incompatible", code: "X", message: "m" } };
    fakeBackend({ "GET /api/health": () => json(body, 503) });
    await expect(api.health()).resolves.toEqual(body);
  });

  it("maps backend error bodies to ApiError", async () => {
    fakeBackend({
      "GET /api/system": () => json({ error: { code: "DB_NEWER_SCHEMA", message: "newer" } }, 503),
    });
    const err = await api.system().catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({ kind: "http", status: 503, code: "DB_NEWER_SCHEMA", message: "newer" });
  });

  it("maps network failures to an unreachable error", async () => {
    fakeBackend({});
    await expect(api.health()).rejects.toMatchObject({ kind: "unreachable" });
  });

  it("times out hung requests", async () => {
    vi.useFakeTimers();
    vi.stubGlobal(
      "fetch",
      vi.fn(
        (_url: string, init: RequestInit) =>
          new Promise((_resolve, reject) => {
            init.signal?.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")));
          }),
      ),
    );
    const pending = api.health().catch((e: unknown) => e);
    await vi.advanceTimersByTimeAsync(REQUEST_TIMEOUT_MS);
    expect(await pending).toMatchObject({ kind: "timeout" });
  });
});
