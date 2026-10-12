"""Account ownership regressions for the newly wired Clerk exchange."""
from unittest.mock import AsyncMock

import jwt
import pytest
from pydantic import SecretStr
from sqlalchemy import func, select

from app.api import clerk_auth
from app.core.clerk_sessions import VerifiedClerkSession
from app.core.config import get_settings
from app.models.external_auth_identity import ExternalAuthIdentity
from app.models.user import User


@pytest.fixture
def verified_clerk(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "clerk_enabled", True)
    monkeypatch.setattr(settings, "clerk_issuer", "https://owned.clerk.accounts.dev")
    monkeypatch.setattr(settings, "clerk_secret_key", SecretStr("synthetic-clerk-secret"))
    verified = VerifiedClerkSession("user_owned", "sess_owned", settings.clerk_issuer)
    monkeypatch.setattr(clerk_auth, "verify_clerk_session_auto", AsyncMock(return_value=verified))
    monkeypatch.setattr(clerk_auth, "_fetch_verified_email_from_clerk", AsyncMock(return_value=None))
    monkeypatch.setattr(clerk_auth, "_verify_active_clerk_session", AsyncMock(return_value=True))
    return verified


async def exchange(client, email="attacker@example.com"):
    return await client.post("/api/auth/clerk/exchange", json={"token": "synthetic", "email": email})


async def test_unverified_payload_cannot_take_over_local_account(client, test_user, session, verified_clerk):
    response = await exchange(client, test_user.email)
    assert response.status_code == 403
    assert await session.scalar(select(func.count()).select_from(ExternalAuthIdentity)) == 0


async def test_payload_cannot_register_verified_account(client, clean_db, session, verified_clerk):
    response = await exchange(client)
    assert response.status_code == 403
    assert await session.scalar(select(func.count()).select_from(User)) == 0


async def test_verified_email_does_not_implicitly_link_existing_user(client, test_user, session, verified_clerk, monkeypatch):
    monkeypatch.setattr(clerk_auth, "_fetch_verified_email_from_clerk", AsyncMock(return_value=test_user.email))
    response = await exchange(client, test_user.email)
    assert response.status_code == 403
    assert await session.scalar(select(func.count()).select_from(ExternalAuthIdentity)) == 0


async def test_disabled_clerk_with_issuer_cannot_exchange(client, clean_db, verified_clerk, monkeypatch):
    monkeypatch.setattr(get_settings(), "clerk_enabled", False)
    assert (await exchange(client)).status_code == 503


async def test_inactive_matching_email_never_receives_token(client, test_user, session, verified_clerk, monkeypatch):
    test_user.is_active = False
    await session.commit()
    monkeypatch.setattr(clerk_auth, "_fetch_verified_email_from_clerk", AsyncMock(return_value=test_user.email))
    assert (await exchange(client, test_user.email)).status_code == 403


async def test_existing_mapping_preserves_identity_without_fresh_auth(client, test_user, session, verified_clerk):
    session.add(ExternalAuthIdentity(provider="clerk", issuer=verified_clerk.issuer,
                                    provider_subject=verified_clerk.user_id, user_id=test_user.id))
    await session.commit()
    before = dict(test_user.preferences)
    response = await exchange(client, "someone-else@example.com")
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["id"] == str(test_user.id)
    assert data["user"]["preferences"] == before
    claims = jwt.decode(data["access_token"], options={"verify_signature": False})
    assert "auth_time" not in claims


@pytest.mark.parametrize("primary_status", ["unverified", None])
async def test_backend_api_requires_verified_primary(monkeypatch, primary_status):
    import httpx
    body = {"id": "user_owned", "primary_email_address_id": "email_primary", "email_addresses": [
        {"id": "email_primary", "email_address": "primary@example.com", "verification": {"status": primary_status}},
        {"id": "email_other", "email_address": "other@example.com", "verification": {"status": "verified"}},
    ]}
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=body))
    real_client = httpx.AsyncClient
    monkeypatch.setattr(clerk_auth.httpx, "AsyncClient", lambda **kwargs: real_client(transport=transport, **kwargs))
    assert await clerk_auth._fetch_verified_email_from_clerk("user_owned", "synthetic") is None


async def test_revoked_session_cannot_exchange(client, test_user, verified_clerk, monkeypatch):
    monkeypatch.setattr(clerk_auth, "_verify_active_clerk_session", AsyncMock(return_value=False))
    assert (await exchange(client, test_user.email)).status_code == 401


@pytest.mark.parametrize("status,user_id", [("revoked", "user_owned"), ("active", "user_other"), ("active", "user_owned")])
async def test_provider_session_subject_and_status(monkeypatch, status, user_id):
    import httpx
    body = {"id": "sess_owned", "user_id": user_id, "status": status}
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=body))
    real_client = httpx.AsyncClient
    monkeypatch.setattr(clerk_auth.httpx, "AsyncClient", lambda **kwargs: real_client(transport=transport, **kwargs))
    assert await clerk_auth._verify_active_clerk_session("sess_owned", "user_owned", "synthetic") is (status == "active" and user_id == "user_owned")


async def test_default_provisioning_failure_rolls_back_user_and_identity(client, clean_db, session, verified_clerk, monkeypatch):
    from fastapi import HTTPException
    from app.models.account import Account
    from app.models.workspace import Workspace
    monkeypatch.setattr(clerk_auth, "_fetch_verified_email_from_clerk", AsyncMock(return_value="new@example.com"))
    monkeypatch.setattr(clerk_auth, "create_default_rules", AsyncMock(side_effect=HTTPException(503, "synthetic provisioning failure")))
    assert (await exchange(client)).status_code == 503
    for model in (User, ExternalAuthIdentity, Account, Workspace):
        assert await session.scalar(select(func.count()).select_from(model)) == 0


async def test_registration_conflict_rolls_back_without_linking_winner(client, clean_db, session, verified_clerk, monkeypatch):
    from sqlalchemy.exc import IntegrityError
    monkeypatch.setattr(clerk_auth, "_fetch_verified_email_from_clerk", AsyncMock(return_value="new@example.com"))
    monkeypatch.setattr(clerk_auth, "create_personal_workspace_for_user", AsyncMock(side_effect=IntegrityError("synthetic insert", {}, Exception("conflict"))))
    assert (await exchange(client)).status_code == 409
    assert await session.scalar(select(func.count()).select_from(User)) == 0
    assert await session.scalar(select(func.count()).select_from(ExternalAuthIdentity)) == 0
