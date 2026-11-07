import type { ApiError } from "../api/client";
import type { Health } from "../api/types";

export function LoadingScreen() {
  return (
    <div role="status" aria-live="polite" className="flex flex-col items-center gap-4 py-24 text-slate-600">
      <span className="h-8 w-8 animate-spin rounded-full border-4 border-slate-200 border-t-indigo-600" aria-hidden />
      <p>Starting OpenFilm Studio…</p>
    </div>
  );
}

export function UnreachableScreen({ error, onRetry }: { error: ApiError; onRetry: () => void }) {
  return (
    <section role="alert" className="mx-auto max-w-xl rounded-xl border border-amber-300 bg-amber-50 p-6">
      <h2 className="text-lg font-semibold text-amber-900">Can't reach the OpenFilm Studio engine</h2>
      <p className="mt-2 text-amber-900">
        {error.kind === "timeout"
          ? "The engine is taking too long to respond."
          : "The engine isn't running or is still starting up."}{" "}
        We'll keep trying automatically.
      </p>
      <p className="mt-2 text-sm text-amber-800">
        If this doesn't go away, close this window and start OpenFilm Studio again with the start
        script. Your projects are safe on this computer.
      </p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-4 rounded-lg bg-amber-700 px-4 py-2 font-medium text-white hover:bg-amber-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500"
      >
        Try again now
      </button>
    </section>
  );
}

export function IncompatibleDatabaseScreen({ health }: { health: Health }) {
  return (
    <section role="alert" className="mx-auto max-w-xl rounded-xl border border-red-300 bg-red-50 p-6">
      <h2 className="text-lg font-semibold text-red-900">Your data needs a newer version of OpenFilm Studio</h2>
      <p className="mt-2 text-red-900">{health.database.message}</p>
      <p className="mt-2 text-sm text-red-800">
        Install the latest version of OpenFilm Studio to open your projects. (This app is version{" "}
        {health.app_version}.)
      </p>
    </section>
  );
}

export function OfflineBanner() {
  return (
    <div role="status" className="bg-slate-800 px-4 py-2 text-center text-sm text-white">
      You're offline. Everything still works on this computer. Only AI generation needs the internet.
    </div>
  );
}
