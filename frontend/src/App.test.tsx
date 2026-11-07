import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import { RETRY_INTERVAL_MS } from "./hooks/useBackend";
import { fakeBackend, json, okHealth, readyBackend, system } from "./test/fakeBackend";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("App", () => {
  it("shows a loading state, then system status from the local backend", async () => {
    readyBackend();
    render(<App />);
    expect(screen.getByRole("status")).toHaveTextContent("Starting OpenFilm Studio");

    expect(await screen.findByText("System status")).toBeInTheDocument();
    expect(screen.getByText("Schema version 2")).toBeInTheDocument();
    expect(screen.getByText(system.data_dir)).toBeInTheDocument();
    expect(screen.getByText(/Demo mode: free and offline/)).toBeInTheDocument();
    expect(screen.getByText("Welcome to OpenFilm Studio")).toBeInTheDocument();
  });

  it("explains an unreachable backend and recovers on retry", async () => {
    const fetchMock = fakeBackend({});
    render(<App />);
    expect(await screen.findByText("Can't reach the OpenFilm Studio engine")).toBeInTheDocument();

    readyBackend();
    await userEvent.click(screen.getByRole("button", { name: "Try again now" }));
    expect(await screen.findByText("System status")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalled();
  });

  it("retries automatically while the backend is starting", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    fakeBackend({});
    render(<App />);
    expect(await screen.findByText("Can't reach the OpenFilm Studio engine")).toBeInTheDocument();

    readyBackend();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(RETRY_INTERVAL_MS);
    });
    expect(await screen.findByText("System status")).toBeInTheDocument();
  });

  it("blocks with a clear message when the database is from a newer version", async () => {
    const fetchMock = fakeBackend({
      "GET /api/health": () =>
        json(
          {
            ...okHealth,
            status: "error",
            database: {
              status: "incompatible",
              code: "DB_NEWER_SCHEMA",
              message: "This data was created by a newer version. Your data was not modified.",
            },
          },
          503,
        ),
    });
    render(<App />);
    expect(
      await screen.findByText("Your data needs a newer version of OpenFilm Studio"),
    ).toBeInTheDocument();
    expect(screen.getByText(/Your data was not modified/)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("dismisses the welcome card through an authenticated local write", async () => {
    readyBackend();
    render(<App />);
    await screen.findByText("Welcome to OpenFilm Studio");

    const put = vi.fn(() => json({ "ui.welcome_dismissed": true }));
    fakeBackend({ "PUT /api/settings/ui.welcome_dismissed": put });
    await userEvent.click(screen.getByRole("button", { name: "Got it" }));

    await waitFor(() => expect(screen.queryByText("Welcome to OpenFilm Studio")).toBeNull());
    const [, init] = put.mock.calls[0] as unknown as [string, RequestInit];
    const headers = init.headers as Record<string, string>;
    expect(headers["X-OpenFilm-Client"]).toBe("web");
    expect(headers["Content-Type"]).toBe("application/json");
    expect(init.body).toBe(JSON.stringify({ value: true }));
  });

  it("keeps the welcome card and shows an error when saving fails", async () => {
    readyBackend();
    render(<App />);
    await screen.findByText("Welcome to OpenFilm Studio");

    fakeBackend({
      "PUT /api/settings/ui.welcome_dismissed": () =>
        json({ error: { code: "DB_LOCKED", message: "Database is busy." } }, 500),
    });
    await userEvent.click(screen.getByRole("button", { name: "Got it" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Database is busy.");
    expect(screen.getByText("Welcome to OpenFilm Studio")).toBeInTheDocument();
  });

  it("hides the welcome card when it was dismissed before (persisted setting)", async () => {
    readyBackend({ "ui.welcome_dismissed": true });
    render(<App />);
    await screen.findByText("System status");
    expect(screen.queryByText("Welcome to OpenFilm Studio")).toBeNull();
  });

  it("shows an offline banner without blocking the local app", async () => {
    readyBackend();
    vi.spyOn(navigator, "onLine", "get").mockReturnValue(false);
    render(<App />);
    expect(await screen.findByText(/You're offline/)).toBeInTheDocument();
    expect(await screen.findByText("System status")).toBeInTheDocument();

    vi.spyOn(navigator, "onLine", "get").mockReturnValue(true);
    act(() => {
      window.dispatchEvent(new Event("online"));
    });
    expect(screen.queryByText(/You're offline/)).toBeNull();
  });
});
