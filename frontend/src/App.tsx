import { Home } from "./components/Home";
import {
  IncompatibleDatabaseScreen,
  LoadingScreen,
  OfflineBanner,
  UnreachableScreen,
} from "./components/StatusScreens";
import { useBackend } from "./hooks/useBackend";
import { useOnlineStatus } from "./hooks/useOnlineStatus";

export function App() {
  const { state, retry, updateSettings } = useBackend();
  const online = useOnlineStatus();

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      {!online && <OfflineBanner />}
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4">
        <h1 className="text-lg font-bold tracking-tight">OpenFilm Studio</h1>
        {state.phase === "ready" && state.system.provider.is_mock && (
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
            Demo mode
          </span>
        )}
      </header>
      <main className="px-6 py-8">
        {state.phase === "loading" && <LoadingScreen />}
        {state.phase === "unreachable" && <UnreachableScreen error={state.error} onRetry={retry} />}
        {state.phase === "incompatible" && <IncompatibleDatabaseScreen health={state.health} />}
        {state.phase === "ready" && (
          <Home system={state.system} settings={state.settings} onSettingsChange={updateSettings} />
        )}
      </main>
    </div>
  );
}
