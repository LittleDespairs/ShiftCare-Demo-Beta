"""Application composition: configuration, resources, lifecycle, and routers."""
from contextlib import asynccontextmanager
from functools import partial

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import database
from shiftcare import config, web
from shiftcare.openapi import build_openapi_schema
from shiftcare.services import runtime, sync_worker
from shiftcare.routes import account_recovery
from shiftcare.routes import auth
from shiftcare.routes import backups
from shiftcare.routes import catalog
from shiftcare.routes import desktop_sync
from shiftcare.routes import employees
from shiftcare.routes import exports
from shiftcare.routes import generation
from shiftcare.routes import invitations
from shiftcare.routes import licensing
from shiftcare.routes import members
from shiftcare.routes import organizations
from shiftcare.routes import pages
from shiftcare.routes import preferences
from shiftcare.routes import schedule
from shiftcare.routes import settings
from shiftcare.routes import shifts
from shiftcare.routes import support
from shiftcare.routes import swaps
from shiftcare.routes import system
from shiftcare.routes import updates


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker = sync_worker.start_desktop_sync_worker()
    try:
        yield
    finally:
        sync_worker.stop_desktop_sync_worker(worker)


def create_app(*, initialize_database: bool = True) -> FastAPI:
    """Compose the HTTP application without putting business logic in the entrypoint."""
    if initialize_database:
        database.init_db()
    app = FastAPI(
        title=config.APP_TITLE,
        description="Web application for nursing staff scheduling",
        version=config.APP_VERSION,
        openapi_tags=config.tags_metadata,
        docs_url=None,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://(127\.0\.0\.1|localhost)(:\d+)?$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )
    app.mount("/static", StaticFiles(directory=str(web.BASE_PATH / "static")), name="static")
    web.templates.env.globals.update(
        app_version=config.APP_VERSION,
        app_name=config.APP_NAME,
        developer_mode_enabled=runtime.is_developer_mode_enabled,
        demo_mode_enabled=runtime.is_demo_mode_enabled,
        cloud_employee_portal_mode=runtime.is_cloud_employee_portal_mode,
    )
    for router in (
        account_recovery.router,
        auth.router,
        backups.router,
        catalog.router,
        desktop_sync.router,
        employees.router,
        exports.router,
        generation.router,
        invitations.router,
        licensing.router,
        members.router,
        organizations.router,
        pages.router,
        preferences.router,
        schedule.router,
        settings.router,
        shifts.router,
        support.router,
        swaps.router,
        system.router,
        updates.router,
    ):
        app.include_router(router)
    app.openapi = partial(build_openapi_schema, app)
    return app
