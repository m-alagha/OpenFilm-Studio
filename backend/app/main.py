"""FastAPI application factory."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import __version__
from app.api import settings as settings_api
from app.api import system as system_api
from app.api.errors import ApiError, api_error_handler
from app.config import Settings, load_settings
from app.db.engine import make_engine
from app.db.migrate import DatabaseCompatibilityError, open_database
from app.paths import prepare_data_dir
from app.security import local_only_middleware

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        data_dir = prepare_data_dir(settings.data_dir)
        app.state.settings = settings
        app.state.db_error = None
        app.state.db_status = None
        engine = make_engine(settings.db_path)
        app.state.engine = engine
        try:
            app.state.db_status = open_database(engine, settings.db_path, data_dir / "backups")
            logger.info(
                "OpenFilm Studio %s ready; schema %s; data in %s",
                __version__,
                app.state.db_status.schema_version,
                data_dir,
            )
        except DatabaseCompatibilityError as exc:
            # Stay up in a blocked state so the UI can explain; never touch the DB.
            engine.dispose()
            app.state.db_error = exc
            logger.error("database refused (%s): %s", exc.code, exc.message)
        try:
            yield
        finally:
            engine.dispose()

    app = FastAPI(
        title="OpenFilm Studio",
        version=__version__,
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    app.middleware("http")(local_only_middleware)
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(system_api.router)
    app.include_router(settings_api.router)
    return app
