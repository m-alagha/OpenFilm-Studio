import { useCallback, useEffect, useState } from "react";

import { ApiError, api } from "../api/client";
import type { UpdateStatus } from "../api/types";

export type UpdateAction = "check" | "snooze" | "skip" | "preferences";

/** Update-manager state from the local backend. All network checks happen there. */
export function useUpdates() {
  const [status, setStatus] = useState<UpdateStatus | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [busy, setBusy] = useState<UpdateAction | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    api
      .updates()
      .then((s) => active && setStatus(s))
      .catch((err: unknown) => {
        if (active) setLoadError(err instanceof ApiError ? err.message : "Couldn't load update settings.");
      });
    return () => {
      active = false;
    };
  }, []);

  const run = useCallback(async (action: UpdateAction, call: () => Promise<UpdateStatus>) => {
    setBusy(action);
    setActionError(null);
    try {
      setStatus(await call());
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setBusy(null);
    }
  }, []);

  return {
    status,
    loadError,
    busy,
    actionError,
    checkNow: () => run("check", api.checkForUpdates),
    snooze: () => run("snooze", api.snoozeUpdate),
    skip: (version: string) => run("skip", () => api.skipUpdate(version)),
    setPreferences: (prefs: { auto_check_enabled?: boolean; disclosure_acknowledged?: boolean }) =>
      run("preferences", () => api.setUpdatePreferences(prefs)),
  };
}
