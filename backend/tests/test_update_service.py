"""Update detection, preferences, skip/snooze, failures and rate limits (offline)."""

from __future__ import annotations

import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from conftest import FakeFetcher, release_json

from app.db.engine import make_engine
from app.db.migrate import open_database
from app.updates.github import FetchError
from app.updates.install import InstallInfo, InstallType
from app.updates.service import UpdateActionError, UpdateService


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kwargs: float) -> None:
        self.now += timedelta(**kwargs)


@pytest.fixture
def clock() -> Clock:
    return Clock()


def make_service(
    tmp_path: Path,
    fetcher: FakeFetcher,
    clock: Clock,
    current: str = "0.1.0",
    env_disabled: bool = False,
) -> UpdateService:
    db = tmp_path / "openfilm.sqlite"
    (tmp_path / "backups").mkdir(parents=True, exist_ok=True)
    engine = make_engine(db)
    open_database(engine, db, tmp_path / "backups")
    install = InstallInfo(InstallType.GIT, "windows", tmp_path)
    return UpdateService(
        engine, current, install, fetcher, disabled_by_environment=env_disabled, clock=clock
    )


def test_defaults_on_but_no_network_before_disclosure(tmp_path: Path, clock: Clock) -> None:
    fetcher = FakeFetcher([release_json("v0.2.0")])
    service = make_service(tmp_path, fetcher, clock)
    status = service.status()
    assert status.auto_check_enabled is True  # D8: on by default
    assert status.disclosure_acknowledged is False
    assert status.last_check_status == "never"
    assert service.should_auto_check() is False
    assert fetcher.calls == 0


def test_auto_check_runs_after_disclosure_and_respects_interval(
    tmp_path: Path, clock: Clock
) -> None:
    fetcher = FakeFetcher([release_json("v0.2.0")])
    service = make_service(tmp_path, fetcher, clock)
    service.set_preferences(disclosure_acknowledged=True)
    assert service.should_auto_check() is True
    service.check(manual=False)
    assert service.should_auto_check() is False
    clock.advance(hours=23)
    assert service.should_auto_check() is False
    clock.advance(hours=1)
    assert service.should_auto_check() is True


def test_disabled_setting_and_environment_block_checks(tmp_path: Path, clock: Clock) -> None:
    fetcher = FakeFetcher([release_json("v0.2.0")])
    service = make_service(tmp_path, fetcher, clock)
    service.set_preferences(disclosure_acknowledged=True, auto_check_enabled=False)
    assert service.should_auto_check() is False

    env_off = make_service(tmp_path / "env", fetcher, clock, env_disabled=True)
    env_off.set_preferences(disclosure_acknowledged=True)
    assert env_off.should_auto_check() is False
    with pytest.raises(UpdateActionError) as info:
        env_off.check(manual=True)
    assert info.value.code == "UPDATES_DISABLED"
    assert fetcher.calls == 0


@pytest.mark.parametrize(
    ("releases", "expected"),
    [
        ([release_json("v0.2.0")], "0.2.0"),
        ([release_json("v0.1.0")], None),  # same version
        ([release_json("v0.0.9")], None),  # older: never offered (no downgrade)
        ([release_json("v0.3.0", draft=True)], None),
        ([release_json("v0.3.0", prerelease=True)], None),
        ([release_json("v0.3.0-rc.1")], None),
        ([release_json("v0.2.0"), release_json("v0.10.0"), release_json("v0.3.0")], "0.10.0"),
        ([], None),
    ],
)
def test_update_detection(
    tmp_path: Path, clock: Clock, releases: list[object], expected: str | None
) -> None:
    service = make_service(tmp_path, FakeFetcher(releases), clock)
    status = service.check(manual=True)
    assert status.last_check_status == "ok"
    assert (str(status.available.version) if status.available else None) == expected
    assert status.notify is (expected is not None)
    # A manual check is one user-initiated request; it never switches on automatic checks.
    assert status.disclosure_acknowledged is False
    assert service.should_auto_check() is False
    assert bool(status.steps) is (expected is not None)


def test_skip_hides_only_that_version(tmp_path: Path, clock: Clock) -> None:
    fetcher = FakeFetcher([release_json("v0.2.0")])
    service = make_service(tmp_path, fetcher, clock)
    service.check(manual=True)
    status = service.skip("0.2.0")
    assert status.skipped and not status.notify
    with pytest.raises(UpdateActionError):
        service.skip("9.9.9")  # only the offered version can be skipped
    fetcher.payload = [release_json("v0.2.0"), release_json("v0.3.0")]
    clock.advance(minutes=2)
    status = service.check(manual=True)
    assert str(status.available.version) == "0.3.0" if status.available else False
    assert status.notify and not status.skipped


def test_snooze_hides_notification_for_three_days(tmp_path: Path, clock: Clock) -> None:
    service = make_service(tmp_path, FakeFetcher([release_json("v0.2.0")]), clock)
    service.check(manual=True)
    assert service.snooze().notify is False
    clock.advance(days=2, hours=23)
    assert service.status().notify is False
    clock.advance(hours=1)
    assert service.status().notify is True


def test_snooze_and_skip_need_an_offered_update(tmp_path: Path, clock: Clock) -> None:
    service = make_service(tmp_path, FakeFetcher([]), clock)
    with pytest.raises(UpdateActionError):
        service.snooze()
    with pytest.raises(UpdateActionError):
        service.skip("0.2.0")


@pytest.mark.parametrize(
    "error",
    [FetchError(FetchError.OFFLINE, "x"), FetchError(FetchError.TIMEOUT, "x"),
     FetchError(FetchError.HTTP_ERROR, "x"), FetchError(FetchError.TOO_LARGE, "x"),
     FetchError(FetchError.BAD_REDIRECT, "x")],
)  # fmt: skip
def test_failures_are_recorded_and_keep_last_known_release(
    tmp_path: Path, clock: Clock, error: FetchError
) -> None:
    fetcher = FakeFetcher([release_json("v0.2.0")])
    service = make_service(tmp_path, fetcher, clock)
    service.check(manual=True)
    fetcher.error = error
    clock.advance(minutes=5)
    status = service.check(manual=True)
    assert status.last_check_status == error.code
    assert status.available is not None and str(status.available.version) == "0.2.0"


@pytest.mark.parametrize("payload", [b"<html>", b"{}", b"null"])
def test_invalid_responses_recorded(tmp_path: Path, clock: Clock, payload: bytes) -> None:
    service = make_service(tmp_path, FakeFetcher(payload), clock)
    assert service.check(manual=True).last_check_status == "invalid_response"


def test_rate_limit_backoff_is_respected(tmp_path: Path, clock: Clock) -> None:
    fetcher = FakeFetcher(error=FetchError(FetchError.RATE_LIMITED, "x", retry_after_s=600))
    service = make_service(tmp_path, fetcher, clock)
    service.set_preferences(disclosure_acknowledged=True)
    assert service.check(manual=True).last_check_status == "rate_limited"
    calls = fetcher.calls
    clock.advance(minutes=5)
    service.check(manual=True)
    assert fetcher.calls == calls  # still inside retry-after: GitHub is not called
    assert service.should_auto_check() is False
    clock.advance(minutes=6)
    fetcher.error = None
    fetcher.payload = []
    assert service.check(manual=True).last_check_status == "ok"


def test_manual_checks_are_throttled_after_success(tmp_path: Path, clock: Clock) -> None:
    fetcher = FakeFetcher([])
    service = make_service(tmp_path, fetcher, clock)
    service.check(manual=True)
    service.check(manual=True)
    assert fetcher.calls == 1
    clock.advance(seconds=61)
    service.check(manual=True)
    assert fetcher.calls == 2


def test_cached_release_not_offered_after_updating(tmp_path: Path, clock: Clock) -> None:
    service = make_service(tmp_path, FakeFetcher([release_json("v0.2.0")]), clock)
    service.check(manual=True)
    engine = service._engine
    after_update = UpdateService(
        engine,
        "0.2.0",
        InstallInfo(InstallType.GIT, "linux", tmp_path),
        FakeFetcher([]),
        clock=clock,
    )
    assert after_update.status().available is None
    assert after_update.status().notify is False


def test_preferences_persist(tmp_path: Path, clock: Clock) -> None:
    service = make_service(tmp_path, FakeFetcher([]), clock)
    service.set_preferences(auto_check_enabled=False, disclosure_acknowledged=True)
    again = UpdateService(
        service._engine, "0.1.0", InstallInfo(InstallType.GIT, "linux", tmp_path), FakeFetcher([])
    )
    status = again.status()
    assert status.auto_check_enabled is False and status.disclosure_acknowledged is True


def test_concurrent_requests_do_not_deadlock(tmp_path: Path, clock: Clock) -> None:
    """Regression: parallel first requests used to fail with 'database is locked'."""
    service = make_service(tmp_path, FakeFetcher([release_json("v0.2.0")]), clock)
    errors: list[BaseException] = []

    def worker(i: int) -> None:
        try:
            for _ in range(10):
                service.status()
                service.set_preferences(auto_check_enabled=bool(i % 2))
        except BaseException as exc:  # noqa: BLE001 - collected for the assertion
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert errors == []


def test_network_wait_does_not_hold_the_database(tmp_path: Path, clock: Clock) -> None:
    started, release = threading.Event(), threading.Event()

    def slow_fetch() -> bytes:
        started.set()
        release.wait(10)
        return b"[]"

    service = make_service(tmp_path, FakeFetcher(), clock)
    service._fetch = slow_fetch
    checker = threading.Thread(target=lambda: service.check(manual=True))
    checker.start()
    try:
        assert started.wait(5)
        t0 = time.monotonic()
        service.status()
        service.set_preferences(auto_check_enabled=False)
        assert time.monotonic() - t0 < 2  # not blocked behind the network call
    finally:
        release.set()
        checker.join(timeout=10)
    assert service.status().last_check_status == "ok"


def test_manual_check_never_enables_automatic_checks(tmp_path: Path, clock: Clock) -> None:
    """D8/D20: only answering the first-run disclosure enables automatic checks."""
    fetcher = FakeFetcher([])
    service = make_service(tmp_path, fetcher, clock)
    service.check(manual=True)
    assert fetcher.calls == 1
    clock.advance(days=2)
    assert service.should_auto_check() is False
    service.check(manual=False)  # the background loop's call
    assert fetcher.calls == 1


def test_automatic_check_rechecks_consent_inside_its_transaction(
    tmp_path: Path, clock: Clock
) -> None:
    fetcher = FakeFetcher([])
    service = make_service(tmp_path, fetcher, clock)
    service.set_preferences(disclosure_acknowledged=True)
    assert service.should_auto_check() is True
    service.set_preferences(auto_check_enabled=False)  # user switches it off meanwhile
    service.check(manual=False)
    assert fetcher.calls == 0
