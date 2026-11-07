"""Update-manager API. Every state change is an explicit user action (POST/PUT)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel, StrictBool, StrictStr

from app.api.errors import ApiError
from app.updates.install import Step, current_arch
from app.updates.service import UpdateActionError, UpdateService, UpdateStatusData

router = APIRouter(prefix="/api/updates")


class StepOut(BaseModel):
    title: str
    detail: str
    command: str | None


class AvailableOut(BaseModel):
    version: str
    name: str
    notes: str
    published_at: str | None
    release_url: str
    download_size: int | None
    skipped: bool
    snoozed_until: datetime | None


class InstallOut(BaseModel):
    type: str
    os: str
    one_click_supported: bool
    one_click_reason: str
    steps: list[StepOut]
    rollback_steps: list[StepOut]


class UpdateStatusOut(BaseModel):
    current_version: str
    auto_check_enabled: bool
    disclosure_acknowledged: bool
    disabled_by_environment: bool
    last_checked_at: datetime | None
    last_check_status: str
    available: AvailableOut | None
    notify: bool
    install: InstallOut


class PreferencesIn(BaseModel):
    auto_check_enabled: StrictBool | None = None
    disclosure_acknowledged: StrictBool | None = None


class SkipIn(BaseModel):
    version: StrictStr


def _steps(steps: list[Step]) -> list[StepOut]:
    return [StepOut(title=s.title, detail=s.detail, command=s.command) for s in steps]


def _download_size(data: UpdateStatusData) -> int | None:
    """Size of the asset for this OS/arch, when the release publishes one."""
    if data.available is None:
        return None
    platform = f"{data.install.os}-{current_arch()}"
    for asset in data.available.assets:
        if platform in asset.name.lower():
            return asset.size
    return None


def to_out(data: UpdateStatusData) -> UpdateStatusOut:
    available = None
    if data.available is not None:
        a = data.available
        available = AvailableOut(
            version=str(a.version),
            name=a.name,
            notes=a.notes,
            published_at=a.published_at,
            release_url=a.release_url,
            download_size=_download_size(data),
            skipped=data.skipped,
            snoozed_until=data.snoozed_until,
        )
    return UpdateStatusOut(
        current_version=data.current_version,
        auto_check_enabled=data.auto_check_enabled,
        disclosure_acknowledged=data.disclosure_acknowledged,
        disabled_by_environment=data.disabled_by_environment,
        last_checked_at=data.last_checked_at,
        last_check_status=data.last_check_status,
        available=available,
        notify=data.notify,
        install=InstallOut(
            type=data.install.type.value,
            os=data.install.os,
            one_click_supported=data.install.one_click_supported,
            one_click_reason=data.install.one_click_reason,
            steps=_steps(data.steps),
            rollback_steps=_steps(data.rollback),
        ),
    )


def _service(request: Request) -> UpdateService:
    state = request.app.state
    if state.db_error is not None:
        raise ApiError(503, state.db_error.code, state.db_error.message)
    service: UpdateService = state.updates
    return service


def _call(fn: Callable[[], UpdateStatusData]) -> UpdateStatusOut:
    try:
        return to_out(fn())
    except UpdateActionError as exc:
        raise ApiError(exc.status, exc.code, exc.message) from exc


@router.get("", response_model=UpdateStatusOut)
def get_status(request: Request) -> UpdateStatusOut:
    return to_out(_service(request).status())


@router.put("/preferences", response_model=UpdateStatusOut)
def put_preferences(body: PreferencesIn, request: Request) -> UpdateStatusOut:
    service = _service(request)
    return _call(
        lambda: service.set_preferences(
            auto_check_enabled=body.auto_check_enabled,
            disclosure_acknowledged=body.disclosure_acknowledged,
        )
    )


@router.post("/check", response_model=UpdateStatusOut)
def post_check(request: Request) -> UpdateStatusOut:
    service = _service(request)
    return _call(lambda: service.check(manual=True))


@router.post("/snooze", response_model=UpdateStatusOut)
def post_snooze(request: Request) -> UpdateStatusOut:
    service = _service(request)
    return _call(service.snooze)


@router.post("/skip", response_model=UpdateStatusOut)
def post_skip(body: SkipIn, request: Request) -> UpdateStatusOut:
    service = _service(request)
    return _call(lambda: service.skip(body.version))


@router.post("/install")
def post_install(request: Request) -> None:
    """One-click installation is disabled until signed installers exist (D9).

    This endpoint never downloads, verifies or runs anything. It exists so the
    refusal is explicit and testable.
    """
    service = _service(request)
    reason = service.status().install.one_click_reason
    raise ApiError(409, "ONE_CLICK_UNSUPPORTED", reason)
