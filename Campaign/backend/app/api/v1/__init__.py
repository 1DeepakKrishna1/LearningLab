"""Aggregate API v1 router."""
from fastapi import APIRouter

from app.api.v1 import (
    analytics,
    audit,
    auth,
    campaigns,
    contacts,
    events,
    providers,
    reports,
    roles,
    segments,
    templates,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(roles.router)
api_router.include_router(templates.router)
api_router.include_router(contacts.router)
api_router.include_router(segments.router)
api_router.include_router(campaigns.router)
api_router.include_router(providers.router)
api_router.include_router(analytics.router)
api_router.include_router(reports.router)
api_router.include_router(events.router)
api_router.include_router(audit.router)
