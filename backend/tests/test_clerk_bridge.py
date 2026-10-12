"""Synthetic keys and fake Clerk sessions; no Clerk API/PII/network needed."""
import time
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.account_deletion import AccountDeletion
from app.models.external_auth_identity import ExternalAuthIdentity
from app.models.user import User

ISSUER = "https://clerk-dev.example.test"
ORIGIN = "http://localhost:3000"
SUBJECT = "user_012345"


@pytest.fixture
def clerk_bridge_config():
    cfg = get_settings()
    previous = {
        "clerk_bridge_enabled": cfg.clerk_bridge_enabled,
        "clerk_issuer": cfg.clerk_issuer,
        "clerk_jwt_public_key": cfg.clerk_jwt_public_key,
        "clerk_authorized_parties": cfg.clerk_authorized_parties,
        "clerk_audience": cfg.clerk_audience,
    }
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    cfg.clerk_bridge_enabled = True
    cfg.clerk_issuer = ISSUER
    cfg.clerk_jwt_public_key = key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    cfg.clerk_authorized_parties = ORIGIN
    cfg.clerk_audience = ""
    yield key
    for name, value in previous.items():
        setattr(cfg, name, value)


def token(key, **changes):
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "sub": SUBJECT,
        "sid": "sess_012345",
        "iat": now,
        "nbf": now - 2,
        "exp": now + 120,
        "azp": ORIGIN,
    }
    claims.update(changes)
    return jwt.encode(claims, key, algorithm="RS256")


def bearer(key, **changes):
    return {"Authorization": "Bearer " + token(key, **changes)}


@pytest.mark.asyncio
async def test_bridge_absent_by_default(client, clean_db):
    cfg = get_settings()
    previous = cfg.clerk_bridge_enabled
    cfg.clerk_bridge_enabled = False
    try:
        response = await client.get("/api/auth/clerk/me")
        assert response.status_code == 404
    finally:
        cfg.clerk_bridge_enabled = previous


@pytest.mark.asyncio
async def test_unlinked_clerk_identity_cannot_inherit_local_user(
    client, test_user: User, clerk_bridge_config
):
    response = await client.get("/api/auth/clerk/me", headers=bearer(clerk_bridge_config))
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_explicit_link_maps_to_original_uuid(
    client, session: AsyncSession, test_user: User, clerk_bridge_config
):
    session.add(ExternalAuthIdentity(
        provider="clerk", issuer=ISSUER, provider_subject=SUBJECT, user_id=test_user.id
    ))
    await session.commit()
    response = await client.get("/api/auth/clerk/me", headers=bearer(clerk_bridge_config))
    assert response.status_code == 200
    assert response.json()["id"] == str(test_user.id)
    assert response.json()["email"] == test_user.email


@pytest.mark.asyncio
@pytest.mark.parametrize("claims", [
    {"sub": "user_someone_else"},
    {"iss": "https://attacker.example"},
    {"azp": "https://attacker.example"},
    {"exp": 1},
    {"sts": "pending"},
    {"act": {"sub": "user_admin"}},
])
async def test_bridge_rejects_unauthorized_claims(
    client, session: AsyncSession, test_user: User, clerk_bridge_config, claims
):
    session.add(ExternalAuthIdentity(
        provider="clerk", issuer=ISSUER, provider_subject=SUBJECT, user_id=test_user.id
    ))
    await session.commit()
    response = await client.get(
        "/api/auth/clerk/me", headers=bearer(clerk_bridge_config, **claims)
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_disabled_user_and_deletion_blocked(
    client, session: AsyncSession, test_user: User, clerk_bridge_config
):
    session.add(ExternalAuthIdentity(
        provider="clerk", issuer=ISSUER, provider_subject=SUBJECT, user_id=test_user.id
    ))
    await session.commit()
    test_user.is_active = False
    session.add(test_user)
    await session.commit()
    assert (await client.get(
        "/api/auth/clerk/me", headers=bearer(clerk_bridge_config)
    )).status_code == 401
    test_user.is_active = True
    session.add(test_user)
    session.add(AccountDeletion(
        id=uuid.uuid4(), user_id=test_user.id,
        tracking_digest="1" * 64, state="executing",
    ))
    await session.commit()
    assert (await client.get(
        "/api/auth/clerk/me", headers=bearer(clerk_bridge_config)
    )).status_code == 401


@pytest.mark.asyncio
async def test_missing_bearer_and_wrong_signing_key(
    client, session: AsyncSession, test_user: User, clerk_bridge_config
):
    session.add(ExternalAuthIdentity(
        provider="clerk", issuer=ISSUER, provider_subject=SUBJECT, user_id=test_user.id
    ))
    await session.commit()
    assert (await client.get("/api/auth/clerk/me")).status_code == 401
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    assert (await client.get(
        "/api/auth/clerk/me", headers=bearer(other_key)
    )).status_code == 401
