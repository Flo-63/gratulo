"""
===============================================================================
Project   : gratulo
Module    : app/main.py
Created   : 2025-10-05
Author    : Florian
Purpose   : This is the main entry point for the Gratulo application.

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""


import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import redis.asyncio as redis
from fastapi_limiter import FastAPILimiter

import logging

from app.htmx import members_htmx, templates_htmx, jobs_htmx, admin_users_htmx
from app.ui import main_ui, members_ui, templates_ui, jobs_ui, mailer_config_ui, auth_ui, legal_ui
from app.api import members_api, groups_api, auth_api, docs_api
from app.services.scheduler import start_scheduler
from app.core.database import engine, Base
from app.core.deps import STATIC_DIR, UPLOADS_DIR
from app.core.constants import ENABLE_REST_API
from app.core.encryption import SECRET_KEY,SESSION_LIFETIME, HTTPS_ONLY
from app.core.logging import setup_logging, get_audit_logger

setup_logging()
logger = logging.getLogger(__name__)
audit_logger = get_audit_logger()

app = FastAPI(
    title="Gratulo API",
    version="0.8.3",
    description=open("app/docs/api_guide.md", encoding="utf-8").read(),
    docs_url="/swagger"if ENABLE_REST_API else None,
    redoc_url="/docs" if ENABLE_REST_API else None,
)

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    max_age=SESSION_LIFETIME * 60,
    same_site="lax",
    https_only=HTTPS_ONLY,
)

# Static mount
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")



if ENABLE_REST_API:
    logger.info("✅ REST API aktiviert – Routen werden registriert.")
    app.include_router(docs_api.docs_api_router, prefix="/api/docs", tags=["API Documentation"])
    app.include_router(auth_api.auth_api_router, prefix="/api/auth", tags=["Authentication"])
    app.include_router(members_api.members_api_router, prefix="/api/members", tags=["Members"])
    app.include_router(groups_api.groups_api_router, prefix="/api/groups", tags=["Groups"])
else:
    logger.warning("🚫 REST API deaktiviert (ENABLE_REST_API=false) – keine API-Routen registriert.")

# Router registrieren
app.include_router(members_htmx.members_htmx_router, include_in_schema=False)      # HTMX
app.include_router(templates_htmx.templates_htmx_router , include_in_schema=False)    # HTMX
app.include_router(jobs_htmx.jobs_htmx_router , include_in_schema=False)

app.include_router(admin_users_htmx.admin_users_router , include_in_schema=False)
app.include_router(main_ui.main_ui_router , include_in_schema=False)             # UI
app.include_router(members_ui.members_ui_router , include_in_schema=False)          # UI
app.include_router(templates_ui.templates_ui_router , include_in_schema=False)        # UI
app.include_router(jobs_ui.jobs_ui_router , include_in_schema=False)
app.include_router(mailer_config_ui.mailer_config_ui_router , include_in_schema=False)
app.include_router(auth_ui.auth_ui_router , include_in_schema=False)
app.include_router(legal_ui.legal_ui_router, include_in_schema=False)

@app.on_event("startup")
async def startup_event():
    """
    Event handler that executes on the startup of the application.

    This handler is responsible for initializing critical components of the
    application, including database table creation, job scheduler startup, as well
    as Redis connection and configuration for rate limiting. It ensures that the
    necessary services are set up for the application to function correctly.

    Raises:
        Exception: If a Redis connection or configuration failure occurs.
    """

    logger = logging.getLogger("uvicorn")

    # Tabellen erzeugen
    Base.metadata.create_all(bind=engine)
    start_scheduler()

    # Redis + Limiter initialisieren
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
    try:
        r = await redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        await r.ping()
        await FastAPILimiter.init(r)
        logger.info(f"✅ Redis connected successfully ({redis_url})")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        logger.warning("Rate limiting disabled until Redis is reachable.")



@app.on_event("shutdown")
async def shutdown_event():
    """
    Handles shutdown events for the application.

    This function is triggered when the application is shutting down.
    It ensures that the FastAPILimiter is properly closed to free resources.

    Raises:
        Any exceptions raised by FastAPILimiter.close().
    """
    await FastAPILimiter.close()