import { useState } from "react";

import type { UpdateStatus, UpdateStep } from "../../api/types";
import { INSTALL_LABELS } from "./format";

function CopyButton({ text }: { text: string }) {
  const [state, setState] = useState<"idle" | "copied" | "failed">("idle");
  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setState("copied");
    } catch {
      setState("failed");
    }
  }
  return (
    <button
      type="button"
      onClick={copy}
      className="shrink-0 rounded-md border border-slate-300 bg-white px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-100"
    >
      {state === "copied" ? "Copied" : state === "failed" ? "Select and copy" : "Copy"}
    </button>
  );
}

function Steps({ steps, label }: { steps: UpdateStep[]; label: string }) {
  return (
    <ol aria-label={label} className="mt-3 flex flex-col gap-3">
      {steps.map((step, i) => (
        <li key={`${i}-${step.title}`} className="flex gap-3">
          <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-sm font-semibold text-indigo-800">
            {i + 1}
          </span>
          <div className="min-w-0 flex-1">
            <p className="font-medium text-slate-900">{step.title}</p>
            {step.detail && <p className="text-sm text-slate-600">{step.detail}</p>}
            {step.command && (
              <div className="mt-1 flex items-center gap-2">
                <code className="block min-w-0 flex-1 overflow-x-auto whitespace-pre rounded-md bg-slate-900 px-3 py-2 font-mono text-sm text-slate-100">
                  {step.command}
                </code>
                <CopyButton text={step.command} />
              </div>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}

/** Installation-specific steps. Never claims to install when it can't. */
export function UpdateGuide({ status, onClose }: { status: UpdateStatus; onClose: () => void }) {
  const { install, available } = status;
  if (!available) return null;
  return (
    <section aria-labelledby="guide-title" className="rounded-xl border border-slate-200 bg-white p-6">
      <div className="flex items-start justify-between gap-4">
        <h2 id="guide-title" className="text-lg font-semibold text-slate-900">
          How to update to {available.version}
        </h2>
        <button type="button" onClick={onClose} className="text-sm text-slate-600 underline hover:text-slate-900">
          Close
        </button>
      </div>
      <p className="mt-1 text-sm text-slate-600">
        Your installation: {INSTALL_LABELS[install.type]}
      </p>
      {!install.one_click_supported && (
        <p className="mt-3 rounded-lg bg-slate-50 p-3 text-sm text-slate-700">{install.one_click_reason}</p>
      )}
      <Steps steps={install.steps} label="Update steps" />
      {install.rollback_steps.length > 0 && (
        <details className="mt-5 rounded-lg border border-slate-200 p-3">
          <summary className="cursor-pointer font-medium text-slate-800">If something goes wrong</summary>
          <Steps steps={install.rollback_steps} label="Recovery steps" />
        </details>
      )}
    </section>
  );
}
