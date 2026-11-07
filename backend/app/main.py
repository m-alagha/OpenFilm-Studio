"""FastAPI application factory."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import __version__
from app.api import settings as settings_api
from app.api import system as system_api
from app.api import updates as updates_api
from app.api.errors import ApiError, api_error_handler
from app.config import Settings, load_settings
from app.datalock import DataDirLock
from app.db.engine import make_engine
from app.db.migrate import DatabaseCompatibilityError, open_database
from app.paths import APP_ROOT, prepare_data_dir
from app.security import local_only_middleware
from app.updates.github import ReleaseFetcher, fetch_releases
from app.updates.install import InstallInfo, current_os, detect_install_type
from app.updates.service import UpdateService

logger = logging.getLogger(__name__)


async def update_loop(service: UpdateService, initial_delay_s: float, poll_s: float) -> None:
    """Background auto-check. Never blocks startup; errors are logged, never raised."""
    await asyncio.sleep(initial_delay_s)
    while True:
        try:
            if await asyncio.to_thread(service.should_auto_check):
                await asyncio.to_thread(service.check, manual=False)
        except Exception:
            logger.exception("background update check failed")
        await asyncio.sleep(poll_s)


def create_app(
    settings: Settings | None = None,
    *,
    data_lock: DataDirLock | None = None,
    release_fetcher: ReleaseFetcher = fetch_releases,
    install: InstallInfo | None = None,
) -> FastAPI:
    settings = settings or load_settings()
    install = install or InstallInfo(detect_install_type(APP_ROOT), current_os(), APP_ROOT)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        data_dir = prepare_data_dir(settings.data_dir)
        # Single instance per data folder: nothing below runs without the lock.
        lock = data_lock if data_lock is not None else DataDirLock(data_dir)
        owns_lock = not lock.held
        lock.acquire()
        app.state.settings = settings
        app.state.db_error = None
        app.state.db_status = None
        app.state.updates = None
        engine = make_engine(settings.db_path)
        app.state.engine = engine
        task: asyncio.Task[None] | None = None
        try:
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
            if app.state.db_error is None:
                service = UpdateService(
                    engine,
                    __version__,
                    install,
                    release_fetcher,
                    disabled_by_environment=settings.update_checks_disabled,
                )
                app.state.updates = service
                task = asyncio.create_task(
                    update_loop(
                        service, settings.update_initial_delay_s, settings.update_poll_interval_s
                    )
                )
            yield
        finally:
            if task is not None:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
            engine.dispose()
            if owns_lock:
                lock.release()

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
    app.include_router(updates_api.router)
    return app
