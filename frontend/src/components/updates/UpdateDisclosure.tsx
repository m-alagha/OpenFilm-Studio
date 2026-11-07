import { useState } from "react";

interface Props {
  busy: boolean;
  onContinue: (autoCheck: boolean) => void;
}

/** First-run disclosure (D8): nothing is requested from GitHub before this is answered. */
export function UpdateDisclosure({ busy, onContinue }: Props) {
  const [autoCheck, setAutoCheck] = useState(true);
  return (
    <section aria-labelledby="disclosure-title" className="rounded-xl border border-slate-200 bg-white p-6">
      <h2 id="disclosure-title" className="text-lg font-semibold text-slate-900">
        Stay up to date
      </h2>
      <p className="mt-2 text-slate-700">
        OpenFilm Studio can check GitHub about once a day for new versions. It only asks for public
        release information. Your projects, settings and API keys are never sent, and nothing is
        downloaded or installed without your OK.
      </p>
      <label className="mt-4 flex items-center gap-3 text-slate-900">
        <input
          type="checkbox"
          checked={autoCheck}
          onChange={(e) => setAutoCheck(e.target.checked)}
          className="h-4 w-4 accent-indigo-600"
        />
        Check for updates automatically
      </label>
      <button
        type="button"
        onClick={() => onContinue(autoCheck)}
        disabled={busy}
        className="mt-4 rounded-lg bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-700 disabled:opacity-60 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400"
      >
        {busy ? "Saving..." : "Continue"}
      </button>
    </section>
  );
}
