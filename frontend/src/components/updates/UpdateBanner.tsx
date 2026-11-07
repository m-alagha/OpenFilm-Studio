import { useState } from "react";

import type { UpdateStatus } from "../../api/types";
import { formatBytes, isOfficialReleaseUrl } from "./format";

interface Props {
  status: UpdateStatus;
  busy: boolean;
  onShowGuide: () => void;
  onSnooze: () => void;
  onSkip: (version: string) => void;
}

/** Non-modal "update available" notification. */
export function UpdateBanner({ status, busy, onShowGuide, onSnooze, onSkip }: Props) {
  const [showNotes, setShowNotes] = useState(false);
  const available = status.available;
  if (!available) return null;
  const oneClick = status.install.one_click_supported;

  return (
    <section
      role="region"
      aria-labelledby="update-title"
      className="rounded-xl border border-emerald-200 bg-emerald-50 p-6"
    >
      <h2 id="update-title" className="text-lg font-semibold text-emerald-950">
        OpenFilm Studio {available.version} is available
      </h2>
      <p className="mt-1 text-emerald-900">
        You have version {status.current_version}.
        {available.download_size !== null && ` Download size: ${formatBytes(available.download_size)}.`}
        {available.published_at && ` Released ${new Date(available.published_at).toLocaleDateString()}.`}
      </p>

      <div className="mt-4 flex flex-wrap gap-2">
        {/* Label reflects reality: no "Update Now" while automatic installation is unsupported. */}
        <button
          type="button"
          onClick={onShowGuide}
          className="rounded-lg bg-emerald-700 px-4 py-2 font-medium text-white hover:bg-emerald-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
        >
          {oneClick ? "Update Now" : "How to Update"}
        </button>
        <button
          type="button"
          onClick={onSnooze}
          disabled={busy}
          className="rounded-lg border border-emerald-700 px-4 py-2 font-medium text-emerald-800 hover:bg-emerald-100 disabled:opacity-60"
        >
          Remind Me Later
        </button>
        <button
          type="button"
          onClick={() => onSkip(available.version)}
          disabled={busy}
          className="rounded-lg px-4 py-2 font-medium text-emerald-800 underline hover:bg-emerald-100 disabled:opacity-60"
        >
          Skip This Version
        </button>
      </div>

      <div className="mt-4">
        <button
          type="button"
          aria-expanded={showNotes}
          onClick={() => setShowNotes((v) => !v)}
          className="text-sm font-medium text-emerald-900 underline"
        >
          {showNotes ? "Hide release notes" : "Show release notes"}
        </button>
        {showNotes && (
          <div className="mt-2 rounded-lg border border-emerald-200 bg-white p-4">
            {/* Plain text only: release notes are never rendered as HTML. */}
            <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-words font-sans text-sm text-slate-800">
              {available.notes || "No release notes were provided."}
            </pre>
            {isOfficialReleaseUrl(available.release_url) && (
              <a
                href={available.release_url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-2 inline-block text-sm text-emerald-900 underline"
              >
                Open the release page on GitHub
              </a>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
