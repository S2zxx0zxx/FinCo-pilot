import time
from unittest.mock import AsyncMock
import pytest
from httpx import AsyncClient
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core.config import get_settings
from app.api import clerk_auth


ISSUER = "https://fincopilot-test.clerk.accounts.dev"
PARTIES = ("http://localhost:3000", "http://localhost:5173")


@pytest.fixture
def clerk_signing_keys():
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = private.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return private, public


def create_clerk_token(private, **updates):
    now = int(time.time())
    payload = {
        "iss": ISSUER,
        "sub": "user_2test12345",
        "sid": "sess_2test12345",
        "azp": "http://localhost:5173",
        "iat": now,
        "nbf": now - 2,
        "exp": now + 120,
    }
    payload.update(updates)
    return jwt.encode(payload, private, algorithm="RS256")


@pytest.mark.asyncio
async def test_clerk_config_endpoint(client: AsyncClient):
    response = await client.get("/api/auth/clerk/config")
    assert response.status_code == 200
    data = response.json()
    assert "enabled" in data
    assert "publishable_key" in data


@pytest.mark.asyncio
async def test_clerk_exchange_unconfigured(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(get_settings(), "clerk_enabled", False)
    monkeypatch.setattr(get_settings(), "clerk_issuer", "")
    response = await client.post(
        "/api/auth/clerk/exchange",
        json={"token": "some.token.here", "email": "test@example.com"},
    )
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_clerk_exchange_invalid_token(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(get_settings(), "clerk_enabled", True)
    monkeypatch.setattr(get_settings(), "clerk_issuer", ISSUER)
    monkeypatch.setattr(get_settings(), "clerk_jwt_public_key", "invalid-pem")
    response = await client.post(
        "/api/auth/clerk/exchange",
        json={"token": "invalid.jwt.token", "email": "test@example.com"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_clerk_exchange_new_user(
    client: AsyncClient, clean_db, clerk_signing_keys, monkeypatch
):
    private, public = clerk_signing_keys
    settings = get_settings()
    monkeypatch.setattr(settings, "clerk_enabled", True)
    monkeypatch.setattr(settings, "clerk_issuer", ISSUER)
    monkeypatch.setattr(settings, "clerk_jwt_public_key", public)
    monkeypatch.setattr(settings, "clerk_authorized_parties", "http://localhost:5173")

    monkeypatch.setattr(clerk_auth, "_fetch_verified_email_from_clerk", AsyncMock(return_value="clerk_user@example.com"))
    from pydantic import SecretStr
    monkeypatch.setattr(settings, "clerk_secret_key", SecretStr("synthetic-clerk-secret"))

    monkeypatch.setattr(clerk_auth, "_verify_active_clerk_session", AsyncMock(return_value=True))
    token = create_clerk_token(private)
    response = await client.post(
        "/api/auth/clerk/exchange",
        json={
            "token": token,
            "email": "clerk_user@example.com",
            "preferences": {"currency_display": "USD", "language": "en"},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "clerk_user@example.com"
    assert data["user"]["preferences"]["currency_display"] == "USD"

    # Verify access token works on protected route
    me_resp = await client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "clerk_user@example.com"

    # Idempotent second exchange returns same user
    second_resp = await client.post(
        "/api/auth/clerk/exchange",
        json={"token": token, "email": "clerk_user@example.com"},
    )
    assert second_resp.status_code == 200
    assert second_resp.json()["user"]["id"] == data["user"]["id"]
