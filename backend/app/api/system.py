from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app import __version__
from app.api.errors import ApiError
from app.db.migrate import SCHEMA_VERSION
from app.providers import MockVideoProvider

router = APIRouter(prefix="/api")


class DatabaseHealth(BaseModel):
    status: str
    code: str | None = None
    message: str | None = None


class Health(BaseModel):
    status: str
    app_version: str
    database: DatabaseHealth


class ProviderInfo(BaseModel):
    provider_id: str
    model_id: str
    is_mock: bool


class SystemInfo(BaseModel):
    app_version: str
    schema_version: int
    supported_schema_version: int
    database_created_by_app_version: str
    data_dir: str
    local_only: bool
    provider: ProviderInfo


@router.get("/health", response_model=Health)
def health(request: Request) -> JSONResponse:
    error = request.app.state.db_error
    if error is None:
        body = Health(status="ok", app_version=__version__, database=DatabaseHealth(status="ok"))
        return JSONResponse(body.model_dump(), status_code=200)
    body = Health(
        status="error",
        app_version=__version__,
        database=DatabaseHealth(status="incompatible", code=error.code, message=error.message),
    )
    return JSONResponse(body.model_dump(), status_code=503)


@router.get("/system", response_model=SystemInfo)
def system(request: Request) -> SystemInfo:
    state = request.app.state
    if state.db_error is not None:
        raise ApiError(503, state.db_error.code, state.db_error.message)
    caps = MockVideoProvider().capabilities()
    return SystemInfo(
        app_version=__version__,
        schema_version=state.db_status.schema_version,
        supported_schema_version=SCHEMA_VERSION,
        database_created_by_app_version=state.db_status.created_by_app_version,
        data_dir=str(state.settings.data_dir),
        local_only=not state.settings.allow_non_loopback,
        provider=ProviderInfo(
            provider_id=caps.provider_id, model_id=caps.model_id, is_mock=caps.is_mock
        ),
    )
