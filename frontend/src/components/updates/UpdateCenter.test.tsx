import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { UpdateStatus } from "../../api/types";
import { App } from "../../App";
import { availableUpdate, fakeBackend, json, okHealth, system, updateStatus } from "../../test/fakeBackend";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

type Routes = Parameters<typeof fakeBackend>[0];

function renderApp(updates: UpdateStatus, routes: Routes = {}) {
  const fetchMock = fakeBackend({
    "GET /api/health": () => json(okHealth),
    "GET /api/system": () => json(system),
    "GET /api/settings": () => json({ "ui.welcome_dismissed": true }),
    "GET /api/updates": () => json(updates),
    ...routes,
  });
  render(<App />);
  return fetchMock;
}

function lastCall(fetchMock: ReturnType<typeof fakeBackend>, key: string) {
  const call = [...fetchMock.mock.calls]
    .reverse()
    .find(([url, init]) => `${init?.method ?? "GET"} ${String(url)}` === key);
  expect(call).toBeDefined();
  const init = call?.[1] as RequestInit;
  return { headers: init.headers as Record<string, string>, body: init.body as string | undefined };
}

describe("first-run disclosure", () => {
  it("asks before any check and saves the user's choice", async () => {
    const put = vi.fn(() => json(updateStatus({ disclosure_acknowledged: true, auto_check_enabled: false })));
    const fetchMock = renderApp(updateStatus({ disclosure_acknowledged: false }), {
      "PUT /api/updates/preferences": put,
    });
    expect(await screen.findByText("Stay up to date")).toBeInTheDocument();
    expect(screen.getByText(/projects, settings and API keys are never sent/)).toBeInTheDocument();

    const box = screen.getByRole("checkbox", { name: "Check for updates automatically" });
    expect(box).toBeChecked(); // D8: on by default
    await userEvent.click(box);
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));

    await waitFor(() => expect(screen.queryByText("Stay up to date")).toBeNull());
    const { headers, body } = lastCall(fetchMock, "PUT /api/updates/preferences");
    expect(headers["X-OpenFilm-Client"]).toBe("web");
    expect(JSON.parse(body ?? "{}")).toEqual({ disclosure_acknowledged: true, auto_check_enabled: false });
    expect(fetchMock.mock.calls.some(([url]) => String(url) === "/api/updates/check")).toBe(false);
  });

  it("is not shown when checks are disabled by the environment", async () => {
    renderApp(updateStatus({ disclosure_acknowledged: false, disabled_by_environment: true }));
    expect(await screen.findByText(/turned off on this computer/)).toBeInTheDocument();
    expect(screen.queryByText("Stay up to date")).toBeNull();
    expect(screen.queryByRole("button", { name: "Check for Updates" })).toBeNull();
  });
});

describe("update notification", () => {
  it("shows versions, size and an honest primary action", async () => {
    renderApp(availableUpdate);
    const banner = await screen.findByRole("region", { name: "OpenFilm Studio 0.2.0 is available" });
    expect(within(banner).getByText(/You have version 0\.1\.0/)).toHaveTextContent("Download size: 50 MB");
    expect(within(banner).getByRole("button", { name: "How to Update" })).toBeInTheDocument();
    expect(within(banner).queryByRole("button", { name: "Update Now" })).toBeNull();
    expect(within(banner).getByRole("button", { name: "Remind Me Later" })).toBeInTheDocument();
    expect(within(banner).getByRole("button", { name: "Skip This Version" })).toBeInTheDocument();
  });

  it("labels the action Update Now only when one-click install is supported", async () => {
    renderApp({ ...availableUpdate, install: { ...availableUpdate.install, one_click_supported: true } });
    expect(await screen.findByRole("button", { name: "Update Now" })).toBeInTheDocument();
  });

  it("renders release notes as plain text, never HTML", async () => {
    renderApp(availableUpdate);
    await userEvent.click(await screen.findByRole("button", { name: "Show release notes" }));
    expect(screen.getByText(/<script>alert\(1\)<\/script>/)).toBeInTheDocument();
    expect(document.querySelector("script")).toBeNull();
    const link = screen.getByRole("link", { name: "Open the release page on GitHub" });
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("does not link to release pages outside the official repository", async () => {
    const base = availableUpdate.available;
    if (!base) throw new Error("fixture must offer an update");
    renderApp({ ...availableUpdate, available: { ...base, release_url: "https://evil.example/x" } });
    await userEvent.click(await screen.findByRole("button", { name: "Show release notes" }));
    expect(screen.queryByRole("link", { name: "Open the release page on GitHub" })).toBeNull();
  });

  it("opens installation-specific steps with copyable commands", async () => {
    const writeText = vi.fn(() => Promise.resolve());
    vi.stubGlobal("navigator", { ...navigator, onLine: true, clipboard: { writeText } });
    renderApp(availableUpdate);
    await userEvent.click(await screen.findByRole("button", { name: "How to Update" }));

    expect(screen.getByRole("heading", { name: "How to update to 0.2.0" })).toBeInTheDocument();
    expect(screen.getByText(/turned off until OpenFilm Studio publishes signed installers/)).toBeInTheDocument();
    const steps = screen.getByRole("list", { name: "Update steps" });
    expect(within(steps).getByText("git checkout v0.2.0")).toBeInTheDocument();
    await userEvent.click(within(steps).getByRole("button", { name: "Copy" }));
    expect(writeText).toHaveBeenCalledWith("git checkout v0.2.0");
    expect(await within(steps).findByRole("button", { name: "Copied" })).toBeInTheDocument();
    expect(screen.getByText("If something goes wrong")).toBeInTheDocument();
  });

  it("remind me later and skip are explicit requests", async () => {
    const snoozed = updateStatus({ ...availableUpdate, notify: false });
    const fetchMock = renderApp(availableUpdate, {
      "POST /api/updates/snooze": () => json(snoozed),
      "POST /api/updates/skip": () => json(snoozed),
    });
    await userEvent.click(await screen.findByRole("button", { name: "Remind Me Later" }));
    await waitFor(() => expect(screen.queryByRole("button", { name: "Remind Me Later" })).toBeNull());
    expect(lastCall(fetchMock, "POST /api/updates/snooze").headers["X-OpenFilm-Client"]).toBe("web");
  });

  it("skip sends the offered version", async () => {
    const fetchMock = renderApp(availableUpdate, {
      "POST /api/updates/skip": () => json({ ...availableUpdate, notify: false }),
    });
    await userEvent.click(await screen.findByRole("button", { name: "Skip This Version" }));
    await waitFor(() => expect(screen.queryByRole("button", { name: "Skip This Version" })).toBeNull());
    expect(JSON.parse(lastCall(fetchMock, "POST /api/updates/skip").body ?? "{}")).toEqual({ version: "0.2.0" });
  });
});

describe("update settings", () => {
  it("checks on request and reports the result", async () => {
    let resolve: (r: Response) => void = () => undefined;
    const fetchMock = renderApp(updateStatus(), {
      "POST /api/updates/check": () => new Promise<Response>((r) => (resolve = r)),
    });
    expect(await screen.findByText("Not checked yet.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Check for Updates" }));
    expect(await screen.findByRole("button", { name: "Checking..." })).toBeDisabled();
    resolve(json(availableUpdate));
    expect(await screen.findByText("Version 0.2.0 is available.")).toBeInTheDocument();
    expect(lastCall(fetchMock, "POST /api/updates/check").headers["X-OpenFilm-Client"]).toBe("web");
  });

  it.each([
    ["offline", /You may be offline/],
    ["rate_limited", /asked us to wait/],
    ["invalid_response", /ignored for your safety/],
    ["ok", /You're up to date/],
  ] as const)("explains check status %s", async (state, message) => {
    renderApp(updateStatus({ last_check_status: state, last_checked_at: "2026-11-07T12:00:00Z" }));
    expect(await screen.findByText(message)).toBeInTheDocument();
  });

  it("says when the available version was skipped", async () => {
    const base = availableUpdate.available;
    if (!base) throw new Error("fixture must offer an update");
    renderApp({ ...availableUpdate, notify: false, available: { ...base, skipped: true } });
    expect(await screen.findByText(/You chose to skip it/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "How to Update" })).toBeNull();
  });

  it("disables manual checks while offline", async () => {
    vi.spyOn(navigator, "onLine", "get").mockReturnValue(false);
    renderApp(updateStatus());
    expect(await screen.findByRole("button", { name: "Check for Updates" })).toBeDisabled();
    expect(screen.getByText(/Connect to the internet to check/)).toBeInTheDocument();
  });

  it("toggles automatic checks", async () => {
    const fetchMock = renderApp(updateStatus(), {
      "PUT /api/updates/preferences": () => json(updateStatus({ auto_check_enabled: false })),
    });
    const box = await screen.findByRole("checkbox", { name: /Check for updates automatically/ });
    await userEvent.click(box);
    await waitFor(() => expect(box).not.toBeChecked());
    expect(JSON.parse(lastCall(fetchMock, "PUT /api/updates/preferences").body ?? "{}")).toEqual({
      auto_check_enabled: false,
    });
  });

  it("shows an error when a check fails", async () => {
    renderApp(updateStatus(), {
      "POST /api/updates/check": () =>
        json({ error: { code: "UPDATES_DISABLED", message: "Update checks are disabled." } }, 409),
    });
    await userEvent.click(await screen.findByRole("button", { name: "Check for Updates" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Update checks are disabled.");
  });

  it("keeps the app usable if update settings can't load", async () => {
    fakeBackend({
      "GET /api/health": () => json(okHealth),
      "GET /api/system": () => json(system),
      "GET /api/settings": () => json({ "ui.welcome_dismissed": true }),
    });
    render(<App />);
    expect(await screen.findByText("System status")).toBeInTheDocument();
    expect(await screen.findByRole("alert")).toHaveTextContent("Update settings are unavailable");
  });
});
