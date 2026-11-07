import type { UpdateStatus } from "../../api/types";
import { INSTALL_LABELS, checkMessage } from "./format";

interface Props {
  status: UpdateStatus;
  online: boolean;
  checking: boolean;
  busy: boolean;
  error: string | null;
  onCheck: () => void;
  onToggleAuto: (enabled: boolean) => void;
}

export function UpdateSettings({ status, online, checking, busy, error, onCheck, onToggleAuto }: Props) {
  const envOff = status.disabled_by_environment;
  return (
    <section aria-labelledby="updates-title" className="rounded-xl border border-slate-200 bg-white p-6">
      <h2 id="updates-title" className="text-lg font-semibold text-slate-900">
        Updates
      </h2>
      <dl className="mt-4 grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-[max-content_1fr]">
        <dt className="font-medium text-slate-600">Current version</dt>
        <dd>{status.current_version}</dd>
        <dt className="font-medium text-slate-600">Installation</dt>
        <dd>{INSTALL_LABELS[status.install.type]}</dd>
        <dt className="font-medium text-slate-600">Last checked</dt>
        <dd>{status.last_checked_at ? new Date(status.last_checked_at).toLocaleString() : "Never"}</dd>
        <dt className="font-medium text-slate-600">Status</dt>
        <dd role="status" aria-live="polite">
          {checking ? "Checking for updates..." : checkMessage(status)}
        </dd>
      </dl>

      {envOff ? (
        <p className="mt-4 rounded-lg bg-slate-50 p-3 text-sm text-slate-700">
          Update checks are turned off on this computer (OPENFILM_UPDATE_CHECK=0).
        </p>
      ) : (
        <>
          <label className="mt-4 flex items-center gap-3 text-slate-900">
            <input
              type="checkbox"
              checked={status.auto_check_enabled}
              disabled={busy}
              onChange={(e) => onToggleAuto(e.target.checked)}
              className="h-4 w-4 accent-indigo-600"
            />
            Check for updates automatically (about once a day)
          </label>
          <button
            type="button"
            onClick={onCheck}
            disabled={busy || !online}
            className="mt-4 rounded-lg border border-slate-300 bg-white px-4 py-2 font-medium text-slate-800 hover:bg-slate-50 disabled:opacity-60"
          >
            {checking ? "Checking..." : "Check for Updates"}
          </button>
          {!online && (
            <p className="mt-2 text-sm text-slate-600">You're offline. Connect to the internet to check for updates.</p>
          )}
        </>
      )}
      {error && (
        <p role="alert" className="mt-3 text-sm text-red-700">
          {error}
        </p>
      )}
      <p className="mt-4 text-xs text-slate-500">
        Only public release information is requested from GitHub. Your projects, settings and keys are never
        sent. Nothing is downloaded or installed automatically.
      </p>
    </section>
  );
}
