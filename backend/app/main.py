"""FastAPI application factory and middleware wiring.

The same `app` object serves local uvicorn and (via lambda_handler.py) AWS
Lambda behind API Gateway. Business routers are registered under `/v1`; health
routers are registered at the root.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings
from app.core.context import RequestContextMiddleware
from app.core.errors import (
    ApiError,
    api_error_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.logging import configure_logging
from app.routers import (
    admin,
    ai,
    auth,
    billing,
    blocks,
    compatibility,
    conversations,
    dev,
    discovery,
    health,
    hidden_profiles,
    interests,
    matches,
    me,
    media,
    moderation,
    notifications,
    profile_biodata,
    profile_brands,
    profile_family,
    profile_media,
    profile_preferences,
    profile_records,
    profile_sections,
    profile_sets,
    profiles,
    reference,
    realtime,
    reports,
    saved_searches,
    shortlist,
    verification,
    webhooks,
)


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    app = FastAPI(
        title="LaariLaara API",
        version="0.1.0",
        description="AI-assisted Punjabi matchmaking platform (serverless variant).",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # Health at root; business routers mount under /v1 as they are built.
    app.include_router(health.router)
    app.include_router(reference.router)
    app.include_router(auth.router)
    app.include_router(me.router)
    app.include_router(profiles.router)
    app.include_router(profiles.invitations_router)
    app.include_router(profile_sections.router)
    app.include_router(profile_sets.router)
    app.include_router(profile_records.router)
    app.include_router(profile_family.router)
    app.include_router(profile_preferences.router)
    app.include_router(profile_brands.router)
    app.include_router(media.router)
    app.include_router(profile_media.router)
    app.include_router(profile_biodata.router)
    app.include_router(discovery.router)
    app.include_router(saved_searches.router)
    app.include_router(shortlist.router)
    app.include_router(hidden_profiles.router)
    app.include_router(compatibility.router)
    app.include_router(interests.router)
    app.include_router(matches.router)
    app.include_router(conversations.router)
    app.include_router(realtime.router)
    app.include_router(ai.profile_ai_router)
    app.include_router(ai.discovery_ai_router)
    app.include_router(ai.compatibility_ai_router)
    app.include_router(ai.conversation_ai_router)
    app.include_router(ai.artifacts_router)
    app.include_router(blocks.router)
    app.include_router(reports.router)
    app.include_router(verification.profile_verification_router)
    app.include_router(verification.verification_requests_router)
    app.include_router(moderation.router)
    app.include_router(notifications.notifications_router)
    app.include_router(notifications.notification_preferences_router)
    app.include_router(notifications.push_endpoints_router)
    app.include_router(billing.billing_router)
    app.include_router(billing.entitlements_router)
    app.include_router(billing.promo_redemptions_router)
    app.include_router(webhooks.router)

    app.include_router(admin.admin_dashboard_router)
    app.include_router(admin.admin_directory_router)
    app.include_router(admin.admin_moderation_router)
    app.include_router(admin.admin_verification_router)
    app.include_router(admin.admin_billing_router)
    app.include_router(admin.admin_support_router)
    app.include_router(admin.admin_config_router)
    app.include_router(admin.admin_reference_router)

    # Local-development conveniences only — never mounted outside local/dev.
    if settings.environment in ("local", "development"):
        app.include_router(dev.router)

    return app


app = create_app()
