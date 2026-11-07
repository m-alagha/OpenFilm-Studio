"""Update-check orchestration and persisted preferences.

Rules (CLAUDE.md Update Safety Policy, D8):
- No network request until the user has seen the first-run disclosure, and never
  when checks are disabled (setting or OPENFILM_UPDATE_CHECK=0).
- Failures are recorded and logged locally; they never raise into startup.
- Only versions newer than the running one are offered (no downgrades).
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.db.models import UpdateState
from app.updates.github import FetchError, ReleaseFetcher
from app.updates.install import InstallInfo, Step, rollback_steps, update_steps
from app.updates.releases import InvalidReleaseData, Release, newest_update, parse_releases
from app.updates.version import InvalidVersion, Version

logger = logging.getLogger(__name__)

AUTO_CHECK_INTERVAL = timedelta(hours=24)
MANUAL_MIN_INTERVAL = timedelta(seconds=60)
SNOOZE_DURATION = timedelta(days=3)
RATE_LIMIT_DEFAULT_BACKOFF = timedelta(hours=1)


class UpdateActionError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


@dataclass(frozen=True)
class UpdateStatusData:
    current_version: str
    auto_check_enabled: bool
    disclosure_acknowledged: bool
    disabled_by_environment: bool
    last_checked_at: datetime | None
    last_check_status: str
    available: Release | None
    skipped: bool
    snoozed_until: datetime | None
    notify: bool
    install: InstallInfo
    steps: list[Step]
    rollback: list[Step]


def _utc(value: datetime | None) -> datetime | None:
    # SQLite returns naive datetimes; everything is stored in UTC.
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


class UpdateService:
    def __init__(
        self,
        engine: Engine,
        current_version: str,
        install: InstallInfo,
        fetcher: ReleaseFetcher,
        *,
        disabled_by_environment: bool = False,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._engine = engine
        self._current = Version.parse(current_version)
        self._install = install
        self._fetch = fetcher
        self._env_disabled = disabled_by_environment
        self._now = clock
        self._lock = threading.Lock()

    # -- state -----------------------------------------------------------------
    @staticmethod
    def _state(session: Session) -> UpdateState:
        state = session.get(UpdateState, 1)
        if state is None:
            # D8: checks default to on, but nothing runs before the disclosure.
            state = UpdateState(id=1, auto_check_enabled=True, disclosure_acknowledged=False)
            session.add(state)
            session.flush()
        return state

    def _cached_release(self, state: UpdateState) -> Release | None:
        if not state.latest_release_json:
            return None
        try:
            release = Release.from_json(state.latest_release_json)
        except (ValueError, KeyError, TypeError, InvalidVersion):
            return None
        return release if release.version > self._current else None

    def status(self) -> UpdateStatusData:
        with Session(self._engine) as session:
            state = self._state(session)
            session.commit()
            return self._status_from(state)

    def _status_from(self, state: UpdateState) -> UpdateStatusData:
        now = self._now()
        available = self._cached_release(state)
        skipped = available is not None and state.skipped_version == str(available.version)
        snoozed_until = _utc(state.snoozed_until)
        snoozed = snoozed_until is not None and now < snoozed_until
        return UpdateStatusData(
            current_version=str(self._current),
            auto_check_enabled=state.auto_check_enabled,
            disclosure_acknowledged=state.disclosure_acknowledged,
            disabled_by_environment=self._env_disabled,
            last_checked_at=_utc(state.last_checked_at),
            last_check_status=state.last_check_status or "never",
            available=available,
            skipped=skipped,
            snoozed_until=snoozed_until if snoozed else None,
            notify=available is not None and not skipped and not snoozed,
            install=self._install,
            steps=update_steps(self._install, available.version, available.release_url)
            if available
            else [],
            rollback=rollback_steps(self._install, self._current) if available else [],
        )

    # -- preferences -------------------------------------------------------------
    def set_preferences(
        self, *, auto_check_enabled: bool | None = None, disclosure_acknowledged: bool | None = None
    ) -> UpdateStatusData:
        with Session(self._engine) as session:
            state = self._state(session)
            if auto_check_enabled is not None:
                state.auto_check_enabled = auto_check_enabled
            if disclosure_acknowledged is not None:
                state.disclosure_acknowledged = disclosure_acknowledged
            session.commit()
            return self._status_from(state)

    def snooze(self) -> UpdateStatusData:
        with Session(self._engine) as session:
            state = self._state(session)
            if self._cached_release(state) is None:
                raise UpdateActionError(409, "NO_UPDATE", "there is no update to postpone")
            state.snoozed_until = self._now() + SNOOZE_DURATION
            session.commit()
            return self._status_from(state)

    def skip(self, version: str) -> UpdateStatusData:
        with Session(self._engine) as session:
            state = self._state(session)
            available = self._cached_release(state)
            if available is None or version != str(available.version):
                raise UpdateActionError(
                    409, "NOT_OFFERED", "only the offered version can be skipped"
                )
            state.skipped_version = version
            state.snoozed_until = None
            session.commit()
            return self._status_from(state)

    # -- checking ----------------------------------------------------------------
    def should_auto_check(self) -> bool:
        with Session(self._engine) as session:
            state = self._state(session)
            session.commit()
            if self._env_disabled or not state.auto_check_enabled:
                return False
            if not state.disclosure_acknowledged:
                return False
            now = self._now()
            retry = _utc(state.retry_not_before)
            if retry is not None and now < retry:
                return False
            last = _utc(state.last_checked_at)
            return last is None or now - last >= AUTO_CHECK_INTERVAL

    def check(self, *, manual: bool) -> UpdateStatusData:
        if self._env_disabled:
            raise UpdateActionError(
                409, "UPDATES_DISABLED", "update checks are disabled by OPENFILM_UPDATE_CHECK=0"
            )
        with self._lock:
            # 1. Short transaction: decide whether to contact GitHub at all.
            with Session(self._engine) as session:
                state = self._state(session)
                # A manual check is a one-off request the user asked for. It does not
                # answer the first-run disclosure, so it never enables automatic checks (D8).
                # Automatic checks re-verify consent here, in case it changed meanwhile.
                if not manual and not (state.auto_check_enabled and state.disclosure_acknowledged):
                    session.commit()
                    return self._status_from(state)
                now = self._now()
                retry = _utc(state.retry_not_before)
                last = _utc(state.last_checked_at)
                rate_limited = retry is not None and now < retry
                throttled = (
                    manual
                    and last is not None
                    and state.last_check_status == "ok"
                    and now - last < MANUAL_MIN_INTERVAL
                )
                session.commit()
                if rate_limited or throttled:
                    return self._status_from(state)
            # 2. Network request with no database lock held.
            outcome = self._fetch_outcome()
            # 3. Short transaction: record the result.
            with Session(self._engine) as session:
                state = self._state(session)
                self._apply(state, outcome, now)
                session.commit()
                return self._status_from(state)

    def _fetch_outcome(self) -> Release | None | FetchError | InvalidReleaseData:
        try:
            releases, rejected = parse_releases(self._fetch())
        except (FetchError, InvalidReleaseData) as exc:
            return exc
        if rejected:
            logger.warning("ignored %d release(s) with invalid metadata", rejected)
        return newest_update(releases, self._current)

    def _apply(
        self,
        state: UpdateState,
        outcome: Release | None | FetchError | InvalidReleaseData,
        now: datetime,
    ) -> None:
        state.last_checked_at = now
        if isinstance(outcome, FetchError):
            state.last_check_status = outcome.code
            if outcome.code == FetchError.RATE_LIMITED:
                backoff = (
                    timedelta(seconds=outcome.retry_after_s)
                    if outcome.retry_after_s is not None
                    else RATE_LIMIT_DEFAULT_BACKOFF
                )
                state.retry_not_before = now + backoff
            logger.info("update check failed: %s", outcome.code)
            return
        if isinstance(outcome, InvalidReleaseData):
            state.last_check_status = "invalid_response"
            logger.warning("update check rejected the release list: %s", outcome)
            return
        state.latest_release_json = outcome.to_json() if outcome else None
        state.last_check_status = "ok"
        state.retry_not_before = None
        logger.info(
            "update check ok: %s", f"{outcome.version} available" if outcome else "up to date"
        )
