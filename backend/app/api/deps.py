from __future__ import annotations

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session

from app.api.errors import ApiError


def get_session(request: Request) -> Iterator[Session]:
    error = request.app.state.db_error
    if error is not None:
        raise ApiError(503, error.code, error.message)
    with Session(request.app.state.engine) as session:
        yield session
