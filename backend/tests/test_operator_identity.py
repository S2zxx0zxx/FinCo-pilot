import pytest

from app.core.config import get_settings


@pytest.mark.asyncio
async def test_app_info_exposes_truthful_nonsecret_operator_identity(client):
    settings = get_settings()
    previous = {
        "operator_identity_enabled": settings.operator_identity_enabled,
        "operator_brand_name": settings.operator_brand_name,
        "operator_entity_type": settings.operator_entity_type,
        "operator_country_code": settings.operator_country_code,
        "operator_legal_name": settings.operator_legal_name,
        "support_enabled": settings.support_enabled,
        "support_email": settings.support_email,
    }

    settings.operator_identity_enabled = True
    settings.operator_brand_name = "FinCo-Pilot"
    settings.operator_entity_type = "individual"
    settings.operator_country_code = "IN"
    settings.operator_legal_name = ""
    settings.support_enabled = True
    settings.support_email = "support@example.com"

    try:
        response = await client.get("/api/info")
        assert response.status_code == 200
        operator = response.json()["operator"]
        assert operator == {
            "brand_name": "FinCo-Pilot",
            "entity_type": "individual",
            "country_code": "IN",
            "legal_name": None,
            "contact_email": "support@example.com",
        }

        serialized = response.text.lower()
        for forbidden in (
            "secret_key",
            "client_secret",
            "refresh_token",
            "razorpay_key_secret",
            "smtp_password",
        ):
            assert forbidden not in serialized
    finally:
        for key, value in previous.items():
            setattr(settings, key, value)


@pytest.mark.asyncio
async def test_app_info_can_hide_operator_identity(client):
    settings = get_settings()
    previous = settings.operator_identity_enabled
    settings.operator_identity_enabled = False
    try:
        response = await client.get("/api/info")
        assert response.status_code == 200
        assert response.json()["operator"] is None
    finally:
        settings.operator_identity_enabled = previous
