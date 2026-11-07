import type { CheckStatus, InstallType, UpdateStatus } from "../../api/types";

const OFFICIAL_RELEASES = "https://github.com/m-alagha/openfilm-studio/releases/";

/** Defence in depth: only ever link to the official repository's release pages. */
export function isOfficialReleaseUrl(url: string): boolean {
  return url.toLowerCase().startsWith(OFFICIAL_RELEASES);
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let value = bytes / 1024;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[unit]}`;
}

export const INSTALL_LABELS: Record<InstallType, string> = {
  git: "Git checkout",
  docker: "Docker container",
  packaged: "Installed app",
  source: "Downloaded source folder",
};

const CHECK_MESSAGES: Record<Exclude<CheckStatus, "ok">, string> = {
  never: "Not checked yet.",
  offline: "Couldn't reach GitHub. You may be offline. OpenFilm Studio keeps working normally.",
  timeout: "GitHub didn't respond in time. We'll try again later.",
  rate_limited: "GitHub asked us to wait before checking again. We'll try later automatically.",
  http_error: "GitHub returned an error. We'll try again later.",
  too_large: "GitHub sent an unexpectedly large response, so it was ignored.",
  bad_redirect: "GitHub redirected to an unexpected address, so the check was stopped.",
  invalid_response: "GitHub returned release data we couldn't verify, so it was ignored for your safety.",
};

export function checkMessage(status: UpdateStatus): string {
  if (status.last_check_status !== "ok") return CHECK_MESSAGES[status.last_check_status];
  if (status.available?.skipped) {
    return `Version ${status.available.version} is available. You chose to skip it; newer versions will still be shown.`;
  }
  if (status.available) return `Version ${status.available.version} is available.`;
  return "You're up to date.";
}
