"""Ownership verification through HTTP and synthetic TLS; never a live inbox claim."""

import re
import time
from email import policy
from email.parser import BytesParser
from urllib.parse import parse_qs, urlsplit
from unittest.mock import AsyncMock, patch

import jwt
import pytest

from app.core.auth import UserManager
from app.core.config import get_settings
from tests.conftest import TestSessionLocal
from tests.test_smtp_delivery import configure, relay as relay


@pytest.mark.asyncio
async def test_tls_link_current_account_replay_and_session_preserved(
    client, test_user, session, auth_headers, monkeypatch, relay, caplog
):
    test_user.is_verified = False
    await session.commit()
    await session.refresh(test_user)
    original = (test_user.hashed_password, test_user.auth_epoch, test_user.is_superuser)
    configure(monkeypatch, relay)
    monkeypatch.setattr(get_settings(), "frontend_url", "https://fincopilot.example")
    with patch("app.api.password_recovery.async_session_maker", TestSessionLocal):
        requested = await client.post(
            "/api/auth/request-verify-token",
            json={"email": test_user.email},
            headers={"Host": "attacker.example"},
        )
    assert requested.status_code == 202 and requested.json() is None
    assert relay.tls and len(relay.messages) == 1
    message = BytesParser(policy=policy.default).parsebytes(relay.messages[0])
    part = message.get_body(preferencelist=("plain",))
    assert part is not None
    match = re.search(r"https://\S+", part.get_content())
    assert match is not None
    link = urlsplit(match.group(0))
    assert link.netloc == "fincopilot.example" and link.path == "/verify-email"
    token = parse_qs(link.query)["token"][0]
    assert (
        token not in requested.text
        and token not in caplog.text
        and test_user.email not in caplog.text
    )
    verified = await client.post("/api/auth/verify", json={"token": token})
    assert verified.status_code == 200 and verified.json()["is_verified"] is True
    assert "access_token" not in verified.json()
    assert (await client.post("/api/auth/verify", json={"token": token})).status_code == 400
    me = await client.get("/api/users/me", headers=auth_headers)
    assert me.status_code == 200 and me.json()["is_verified"] is True
    await session.refresh(test_user)
    assert (test_user.hashed_password, test_user.auth_epoch, test_user.is_superuser) == original


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    [
        "missing_exp",
        "expired",
        "string_exp",
        "boolean_exp",
        "bad_subject",
        "missing_email",
        "invalid_email",
        "bad_email_type",
        "wrong_audience",
        "wrong_secret",
        "mismatched_email",
        "inactive",
        "email_changed",
    ],
)
async def test_invalid_claims_and_current_state_cannot_verify(client, test_user, session, case):
    test_user.is_verified = False
    await session.commit()
    claims = {
        "sub": str(test_user.id),
        "email": test_user.email,
        "aud": UserManager.verification_token_audience,
        "exp": int(time.time()) + 600,
    }
    if case == "missing_exp":
        claims.pop("exp")
    elif case == "expired":
        claims["exp"] = int(time.time()) - 1
    elif case == "string_exp":
        claims["exp"] = str(claims["exp"])
    elif case == "boolean_exp":
        claims["exp"] = True
    elif case == "bad_subject":
        claims["sub"] = ["bad"]
    elif case == "missing_email":
        claims.pop("email")
    elif case == "invalid_email":
        claims["email"] = "invalid"
    elif case == "bad_email_type":
        claims["email"] = {"bad": True}
    elif case == "wrong_audience":
        claims["aud"] = "fastapi-users:auth"
    elif case == "mismatched_email":
        claims["email"] = "other@example.com"
    key = (
        "synthetic-wrong-verification-signing-key"
        if case == "wrong_secret"
        else get_settings().secret_key.get_secret_value()
    )
    token = jwt.encode(claims, key, algorithm="HS256")
    if case == "inactive":
        test_user.is_active = False
    elif case == "email_changed":
        test_user.email = "changed@example.com"
    await session.commit()
    response = await client.post("/api/auth/verify", json={"token": token})
    assert response.status_code == 400 and response.json()["detail"] == "VERIFY_USER_BAD_TOKEN"
    await session.refresh(test_user)
    assert test_user.is_verified is False and token not in response.text


@pytest.mark.asyncio
async def test_unknown_verified_inactive_and_provider_failure_are_generic(
    client, test_user, session, caplog
):
    failed = AsyncMock(side_effect=RuntimeError("synthetic provider failure"))
    with (
        patch("app.api.password_recovery.async_session_maker", TestSessionLocal),
        patch("app.core.auth.send_verification_email", failed),
    ):
        verified = await client.post(
            "/api/auth/request-verify-token", json={"email": test_user.email}
        )
        unknown = await client.post(
            "/api/auth/request-verify-token", json={"email": "unknown@example.com"}
        )
        test_user.is_verified = False
        await session.commit()
        known = await client.post("/api/auth/request-verify-token", json={"email": test_user.email})
        test_user.is_active = False
        await session.commit()
        inactive = await client.post(
            "/api/auth/request-verify-token", json={"email": test_user.email}
        )
    assert [r.status_code for r in (verified, unknown, known, inactive)] == [202] * 4
    assert verified.content == unknown.content == known.content == inactive.content
    failed.assert_awaited_once()
    assert test_user.email not in caplog.text


@pytest.mark.asyncio
async def test_signup_schedules_initial_mail_and_failure_does_not_undo_account(client):
    failed = AsyncMock(side_effect=RuntimeError("synthetic provider failure"))
    with (
        patch("app.api.password_recovery.async_session_maker", TestSessionLocal),
        patch("app.core.auth.send_verification_email", failed),
    ):
        response = await client.post(
            "/api/auth/register",
            json={"email": "signup-verification@example.com", "password": "Synthetic-signup-123"},
        )
    assert response.status_code == 201 and response.json()["is_verified"] is False
    failed.assert_awaited_once()
    login = await client.post(
        "/api/auth/login",
        data={"username": "signup-verification@example.com", "password": "Synthetic-signup-123"},
    )
    assert login.status_code == 200
    delivered = AsyncMock(return_value=True)
    with (
        patch("app.api.password_recovery.async_session_maker", TestSessionLocal),
        patch("app.core.auth.send_verification_email", delivered),
    ):
        assert (
            await client.post(
                "/api/auth/request-verify-token", json={"email": "signup-verification@example.com"}
            )
        ).status_code == 202
    delivered.assert_awaited_once()


@pytest.mark.asyncio
async def test_verification_recipient_quota_is_private_and_separate_from_reset(
    client, test_user, monkeypatch
):
    from app.api import password_recovery
    from fastapi import HTTPException

    captured = []

    async def deny(key):
        captured.append(key)
        raise HTTPException(429, "Too many requests", headers={"Retry-After": "3600"})

    monkeypatch.setattr(password_recovery._recipient_limit, "check_key", deny)
    deliver = AsyncMock()
    monkeypatch.setattr(password_recovery, "_deliver", deliver)
    for path in ("request-verify-token", "forgot-password"):
        for email in (test_user.email, "unknown@example.com"):
            response = await client.post("/api/auth/" + path, json={"email": email})
            assert response.status_code == 429 and response.headers["Retry-After"] == "3600"
    assert captured[0].startswith("email_verification:recipient:")
    assert captured[2].startswith("password_recovery:recipient:")
    assert captured[0].rsplit(":", 1)[1] == captured[2].rsplit(":", 1)[1]
    assert all("@" not in key and len(key.rsplit(":", 1)[1]) == 64 for key in captured)
    deliver.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["configuration", "capacity"])
async def test_request_availability_is_account_independent_and_signup_stays_committed(
    client, test_user, monkeypatch, failure
):
    from app.api import password_recovery

    if failure == "configuration":
        monkeypatch.setattr(get_settings(), "email_delivery_required", True)
        monkeypatch.setattr(get_settings(), "smtp_host", "")
    else:
        monkeypatch.setattr(password_recovery, "_active_requests", password_recovery._MAX_ACTIVE)
    deliver = AsyncMock()
    monkeypatch.setattr(password_recovery, "_deliver", deliver)
    responses = []
    for email in (test_user.email, "unknown@example.com"):
        response = await client.post("/api/auth/request-verify-token", json={"email": email})
        responses.append(response)
        assert response.status_code == 503 and email not in response.text
    assert responses[0].content == responses[1].content
    signup = await client.post(
        "/api/auth/register",
        json={"email": "unavailable-signup@example.com", "password": "Synthetic-signup-123"},
    )
    assert signup.status_code == 201 and signup.json()["is_verified"] is False
    deliver.assert_not_awaited()


@pytest.mark.asyncio
async def test_email_change_resets_ownership_and_rejects_prechange_link(
    client, test_user, session, auth_headers
):
    await session.refresh(test_user)
    token = jwt.encode(
        {
            "sub": str(test_user.id),
            "email": test_user.email,
            "aud": UserManager.verification_token_audience,
            "exp": int(time.time()) + 600,
        },
        get_settings().secret_key.get_secret_value(),
        algorithm="HS256",
    )
    changed = await client.patch(
        "/api/users/me", headers=auth_headers, json={"email": "new-ownership@example.com"}
    )
    assert changed.status_code == 200 and changed.json()["is_verified"] is False
    assert (await client.post("/api/auth/verify", json={"token": token})).status_code == 400
    await session.refresh(test_user)
    assert test_user.email == "new-ownership@example.com" and not test_user.is_verified


@pytest.mark.asyncio
async def test_verification_preserves_mfa_and_does_not_issue_session(
    client, test_user, session, auth_headers
):
    import pyotp

    setup = await client.post("/api/auth/2fa/setup", headers=auth_headers)
    assert setup.status_code == 200
    enabled = await client.post(
        "/api/auth/2fa/enable",
        headers=auth_headers,
        json={"code": pyotp.TOTP(setup.json()["secret"]).now()},
    )
    assert enabled.status_code == 200
    await session.refresh(test_user)
    before = (test_user.totp_secret, test_user.recovery_code_hashes, test_user.auth_epoch)
    test_user.is_verified = False
    await session.commit()
    token = jwt.encode(
        {
            "sub": str(test_user.id),
            "email": test_user.email,
            "aud": UserManager.verification_token_audience,
            "exp": int(time.time()) + 600,
        },
        get_settings().secret_key.get_secret_value(),
        algorithm="HS256",
    )
    response = await client.post("/api/auth/verify", json={"token": token})
    assert response.status_code == 200 and "access_token" not in response.json()
    await session.refresh(test_user)
    assert test_user.is_2fa_enabled
    assert (test_user.totp_secret, test_user.recovery_code_hashes, test_user.auth_epoch) == before
    login = await client.post(
        "/api/auth/login", data={"username": test_user.email, "password": "testpass123"}
    )
    assert login.status_code == 200 and login.json()["requires_2fa"] is True
    assert "access_token" not in login.json()


@pytest.mark.asyncio
async def test_manager_refreshes_stale_identity_before_ownership_decision(test_user, session):
    from fastapi_users import exceptions
    from fastapi_users.db import SQLAlchemyUserDatabase
    from sqlalchemy import update
    from app.models.user import User

    test_user.is_verified = False
    await session.commit()
    token = jwt.encode(
        {
            "sub": str(test_user.id),
            "email": test_user.email,
            "aud": UserManager.verification_token_audience,
            "exp": int(time.time()) + 600,
        },
        get_settings().secret_key.get_secret_value(),
        algorithm="HS256",
    )
    async with TestSessionLocal() as other:
        await other.execute(update(User).where(User.id == test_user.id).values(is_active=False))
        await other.commit()
    assert test_user.is_active is True
    manager = UserManager(SQLAlchemyUserDatabase(session, User))
    with pytest.raises(exceptions.InvalidVerifyToken):
        await manager.verify(token)
    assert test_user.is_active is False and test_user.is_verified is False
