import { useCallback, useEffect, useState } from "react";

import { ApiError, api } from "../api/client";
import type { AppSettings, Health, SystemInfo } from "../api/types";

export const RETRY_INTERVAL_MS = 3000;

export type BackendState =
  | { phase: "loading" }
  | { phase: "unreachable"; error: ApiError }
  | { phase: "incompatible"; health: Health }
  | { phase: "ready"; system: SystemInfo; settings: AppSettings };

function toApiError(err: unknown): ApiError {
  return err instanceof ApiError ? err : new ApiError("unreachable", "Something went wrong.");
}

/** Connects to the local backend, retrying automatically while it is unreachable. */
export function useBackend() {
  const [state, setState] = useState<BackendState>({ phase: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true; // ignore results from superseded attempts
    let retryTimer: ReturnType<typeof setTimeout> | undefined;

    (async () => {
      try {
        const health = await api.health();
        if (health.database.status !== "ok") {
          if (active) setState({ phase: "incompatible", health });
          return;
        }
        const [system, settings] = await Promise.all([api.system(), api.settings()]);
        if (active) setState({ phase: "ready", system, settings });
      } catch (err) {
        if (!active) return;
        setState({ phase: "unreachable", error: toApiError(err) });
        retryTimer = setTimeout(() => setAttempt((n) => n + 1), RETRY_INTERVAL_MS);
      }
    })();

    return () => {
      active = false;
      clearTimeout(retryTimer);
    };
  }, [attempt]);

  const retry = useCallback(() => {
    setState({ phase: "loading" });
    setAttempt((n) => n + 1);
  }, []);

  const updateSettings = useCallback((settings: AppSettings) => {
    setState((prev) => (prev.phase === "ready" ? { ...prev, settings } : prev));
  }, []);

  return { state, retry, updateSettings };
}
