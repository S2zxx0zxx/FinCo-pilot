"""Public capability/feature-flag endpoint.

Tells the frontend which optional features are enabled so it can hide
nav items, routes, etc. Lightweight — no auth required.
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.support import public_support_info
from app.core.config import get_settings
from app.core.feature_flags import feature_flag

router = APIRouter(prefix="/api", tags=["info"])


@router.get("/privacy-policy")
async def get_privacy_policy():
    from app.core.privacy_policy import public_policy
    return JSONResponse(public_policy(get_settings()), headers={"Cache-Control": "no-store"})


@router.get("/terms")
async def get_terms():
    from app.core.terms import public_terms
    return JSONResponse(public_terms(get_settings()), headers={"Cache-Control": "no-store"})


@router.get("/info")
async def get_app_info():
    settings = get_settings()
    operator = None
    if settings.operator_identity_enabled:
        legal_name = settings.operator_legal_name.strip() or None
        operator = {
            "brand_name": settings.operator_brand_name.strip(),
            "entity_type": settings.operator_entity_type.strip().lower(),
            "country_code": settings.operator_country_code.strip().upper(),
            "legal_name": legal_name,
            # Reuse the configured human-support destination rather than
            # inventing a second public contact identity.
            "contact_email": (
                settings.support_email.strip()
                if settings.support_enabled and settings.support_email.strip()
                else None
            ),
        }

    return {
        "features": {
            "agents": feature_flag("AGENTS_ENABLED"),
            "tesouro_direto": feature_flag("TESOURO_DIRETO_ENABLED"),
        },
        "support": public_support_info().model_dump(),
        "operator": operator,
    }
