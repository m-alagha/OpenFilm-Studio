import { useState, type ReactNode } from "react";

import { useUpdates } from "../../hooks/useUpdates";
import { UpdateBanner } from "./UpdateBanner";
import { UpdateDisclosure } from "./UpdateDisclosure";
import { UpdateGuide } from "./UpdateGuide";
import { UpdateSettings } from "./UpdateSettings";

/** Wraps the home screen with the update notification (top) and settings (bottom). */
export function UpdateCenter({ online, children }: { online: boolean; children: ReactNode }) {
  const updates = useUpdates();
  const [guideOpen, setGuideOpen] = useState(false);
  const { status } = updates;
  const busy = updates.busy !== null;

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      {status && !status.disclosure_acknowledged && !status.disabled_by_environment && (
        <UpdateDisclosure
          busy={busy}
          onContinue={(autoCheck) =>
            updates.setPreferences({ disclosure_acknowledged: true, auto_check_enabled: autoCheck })
          }
        />
      )}
      {status?.notify && (
        <UpdateBanner
          status={status}
          busy={busy}
          onShowGuide={() => setGuideOpen(true)}
          onSnooze={() => {
            setGuideOpen(false);
            updates.snooze();
          }}
          onSkip={(version) => {
            setGuideOpen(false);
            updates.skip(version);
          }}
        />
      )}
      {status && guideOpen && status.available && (
        <UpdateGuide status={status} onClose={() => setGuideOpen(false)} />
      )}
      {children}
      {status && (
        <UpdateSettings
          status={status}
          online={online}
          checking={updates.busy === "check"}
          busy={busy}
          error={updates.actionError}
          onCheck={() => {
            setGuideOpen(false);
            updates.checkNow();
          }}
          onToggleAuto={(enabled) => updates.setPreferences({ auto_check_enabled: enabled })}
        />
      )}
      {updates.loadError && (
        <p role="alert" className="text-sm text-red-700">
          Update settings are unavailable: {updates.loadError}
        </p>
      )}
    </div>
  );
}
