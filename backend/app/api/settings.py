"""User-visible app settings. Only registered keys with typed values are accepted.

Credentials are never settings: API keys go to the OS credential store (M5).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.api.errors import ApiError
from app.db.models import AppSetting

router = APIRouter(prefix="/api/settings")

# key -> (type, default)
REGISTRY: dict[str, tuple[type, Any]] = {
    "ui.welcome_dismissed": (bool, False),
}

SessionDep = Annotated[Session, Depends(get_session)]


class SettingValue(BaseModel):
    value: Any


def _current(session: Session) -> dict[str, Any]:
    values = {key: default for key, (_type, default) in REGISTRY.items()}
    for row in session.scalars(select(AppSetting)):
        if row.key in REGISTRY:
            values[row.key] = json.loads(row.value_json)
    return values


@router.get("")
def list_settings(session: SessionDep) -> dict[str, Any]:
    return _current(session)


@router.put("/{key}")
def put_setting(key: str, body: SettingValue, session: SessionDep) -> dict[str, Any]:
    if key not in REGISTRY:
        raise ApiError(404, "UNKNOWN_SETTING", f"unknown setting {key!r}")
    expected, _default = REGISTRY[key]
    if type(body.value) is not expected:
        raise ApiError(422, "INVALID_SETTING", f"{key} must be {expected.__name__}")
    row = session.get(AppSetting, key)
    now = datetime.now(UTC)
    encoded = json.dumps(body.value)
    if row is None:
        session.add(AppSetting(key=key, value_json=encoded, updated_at=now))
    else:
        row.value_json = encoded
        row.updated_at = now
    session.commit()
    return _current(session)
