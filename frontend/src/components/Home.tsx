import { useState } from "react";

import { ApiError, api } from "../api/client";
import type { AppSettings, SystemInfo } from "../api/types";

interface HomeProps {
  system: SystemInfo;
  settings: AppSettings;
  onSettingsChange: (settings: AppSettings) => void;
}

export function Home({ system, settings, onSettingsChange }: HomeProps) {
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  async function dismissWelcome() {
    setSaving(true);
    setSaveError(null);
    try {
      onSettingsChange(await api.setSetting("ui.welcome_dismissed", true));
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.message : "Couldn't save.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      {!settings["ui.welcome_dismissed"] && (
        <section aria-labelledby="welcome-title" className="rounded-xl border border-indigo-200 bg-indigo-50 p-6">
          <h2 id="welcome-title" className="text-xl font-semibold text-indigo-950">
            Welcome to OpenFilm Studio
          </h2>
          <p className="mt-2 text-indigo-950">
            Everything you create stays on this computer. Nothing is uploaded unless you choose to
            generate a scene with an AI provider, and you'll always see what is sent first.
          </p>
          {saveError && (
            <p role="alert" className="mt-3 text-sm text-red-700">
              Couldn't save your choice: {saveError} Please try again.
            </p>
          )}
          <button
            type="button"
            onClick={dismissWelcome}
            disabled={saving}
            className="mt-4 rounded-lg bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-700 disabled:opacity-60 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400"
          >
            {saving ? "Saving…" : "Got it"}
          </button>
        </section>
      )}

      <section aria-labelledby="status-title" className="rounded-xl border border-slate-200 bg-white p-6">
        <h2 id="status-title" className="text-lg font-semibold text-slate-900">
          System status
        </h2>
        <dl className="mt-4 grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-[max-content_1fr]">
          <dt className="font-medium text-slate-600">Engine</dt>
          <dd className="text-emerald-700">Connected (this computer only)</dd>
          <dt className="font-medium text-slate-600">Version</dt>
          <dd>{system.app_version}</dd>
          <dt className="font-medium text-slate-600">Database</dt>
          <dd>Schema version {system.schema_version}</dd>
          <dt className="font-medium text-slate-600">Your data folder</dt>
          <dd className="break-all font-mono text-sm">{system.data_dir}</dd>
          <dt className="font-medium text-slate-600">AI provider</dt>
          <dd>
            {system.provider.is_mock
              ? "Demo mode: free and offline. No real videos are generated yet."
              : system.provider.provider_id}
          </dd>
        </dl>
      </section>
    </div>
  );
}
