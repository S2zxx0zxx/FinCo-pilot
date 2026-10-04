"""HTTP journey with a real synthetic TLS SMTP relay; no live inbox claims."""

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
from tests.test_smtp_delivery import configure, relay as relay  # shared real TLS fixture


@pytest.mark.asyncio
async def test_real_tls_email_link_reset_replay_sessions_and_login(
    client, auth_headers, test_user, monkeypatch, relay, caplog
):
    configure(monkeypatch, relay)
    monkeypatch.setattr(get_settings(), "frontend_url", "https://fincopilot.example")
    notice = AsyncMock(return_value=True)
    with (
        patch("app.api.password_recovery.async_session_maker", TestSessionLocal),
        patch("app.core.auth.send_password_changed_email", notice),
    ):
        response = await client.post(
            "/api/auth/forgot-password",
            json={"email": test_user.email},
            headers={"Host": "attacker.example"},
        )
        assert response.status_code == 202 and response.json() is None
        assert relay.tls and len(relay.messages) == 1
        message = BytesParser(policy=policy.default).parsebytes(relay.messages[0])
        part = message.get_body(preferencelist=("plain",))
        assert part is not None
        body = part.get_content()
        match = re.search(r"https://\S+", body)
        assert match is not None
        link = match.group(0)
        url = urlsplit(link)
        assert url.netloc == "fincopilot.example" and url.path == "/reset-password"
        token = parse_qs(url.query)["token"][0]
        assert (
            token not in response.text
            and token not in caplog.text
            and test_user.email not in caplog.text
        )
        assert (await client.get("/api/users/me", headers=auth_headers)).status_code == 200
        assert (
            await client.post(
                "/api/auth/reset-password", json={"token": token, "password": "short"}
            )
        ).status_code == 400
        assert (
            await client.post(
                "/api/auth/reset-password", json={"token": token, "password": "New-password-123"}
            )
        ).status_code == 200
        notice.assert_awaited_once_with(test_user.email)
        assert (
            await client.post(
                "/api/auth/reset-password", json={"token": token, "password": "Replay-password-123"}
            )
        ).status_code == 400
        assert (await client.get("/api/users/me", headers=auth_headers)).status_code == 401
        assert (
            await client.post(
                "/api/auth/login", data={"username": test_user.email, "password": "testpass123"}
            )
        ).status_code == 400
        login = await client.post(
            "/api/auth/login", data={"username": test_user.email, "password": "New-password-123"}
        )
        assert login.status_code == 200
        assert (
            await client.get(
                "/api/users/me", headers={"Authorization": "Bearer " + login.json()["access_token"]}
            )
        ).status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    [
        "missing_exp",
        "expired",
        "string_exp",
        "bad_subject",
        "bad_fingerprint",
        "wrong_audience",
        "wrong_secret",
        "unknown_hash",
        "boolean_exp",
        "missing_fgpt",
    ],
)
async def test_malformed_reset_tokens_are_bounded_and_do_not_change_credentials(
    client, test_user, session, case
):
    claims = {
        "sub": str(test_user.id),
        "aud": UserManager.reset_password_token_audience,
        "exp": int(time.time()) + 600,
        "password_fgpt": "unknown-hash",
    }
    if case == "missing_exp":
        claims.pop("exp")
    elif case == "expired":
        claims["exp"] = int(time.time()) - 600
    elif case == "string_exp":
        claims["exp"] = str(claims["exp"])
    elif case == "bad_subject":
        claims["sub"] = ["invalid"]
    elif case == "bad_fingerprint":
        claims["password_fgpt"] = {"invalid": True}
    elif case == "wrong_audience":
        claims["aud"] = "fastapi-users:auth"
    if case == "boolean_exp":
        claims["exp"] = True
    elif case == "missing_fgpt":
        claims.pop("password_fgpt")
    key = (
        "synthetic-wrong-key-long-enough-for-hs256"
        if case == "wrong_secret"
        else get_settings().secret_key.get_secret_value()
    )
    token = jwt.encode(claims, key, algorithm="HS256")
    old = test_user.hashed_password
    response = await client.post(
        "/api/auth/reset-password", json={"token": token, "password": "New-password-123"}
    )
    assert response.status_code == 400 and response.json()["detail"] == "RESET_PASSWORD_BAD_TOKEN"
    assert token not in response.text
    await session.refresh(test_user)
    assert test_user.hashed_password == old


@pytest.mark.asyncio
async def test_recovery_unknown_inactive_and_smtp_failure_return_same_acceptance(
    client, test_user, session, caplog
):
    from app.core.smtp_runtime import EmailDeliveryError

    failed = AsyncMock(side_effect=EmailDeliveryError("recipient_refused"))
    with (
        patch("app.api.password_recovery.async_session_maker", TestSessionLocal),
        patch("app.core.auth.send_password_reset_email", failed),
    ):
        known = await client.post("/api/auth/forgot-password", json={"email": test_user.email})
        unknown = await client.post(
            "/api/auth/forgot-password", json={"email": "unknown@example.com"}
        )
        test_user.is_active = False
        await session.commit()
        inactive = await client.post("/api/auth/forgot-password", json={"email": test_user.email})
    assert [r.status_code for r in (known, unknown, inactive)] == [202, 202, 202]
    assert known.content == unknown.content == inactive.content
    failed.assert_awaited_once()
    assert test_user.email not in caplog.text


@pytest.mark.asyncio
async def test_inventory_credential_is_stale_after_reset(
    client, test_user, test_workspace, session
):
    from fastapi_users.db import SQLAlchemyUserDatabase
    from app.models.mcp_token import ExternalMCPToken
    from app.core.auth import get_jwt_strategy
    from datetime import datetime, timedelta, timezone
    import uuid

    row = ExternalMCPToken(
        id=uuid.uuid4(),
        user_id=test_user.id,
        workspace_id=test_workspace.id,
        credential_stamp=get_jwt_strategy().stamp(test_user),
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        allow_writes=False,
    )
    session.add(row)
    await session.commit()
    captured = AsyncMock()
    manager = UserManager(SQLAlchemyUserDatabase(session, type(test_user)))
    with (
        patch.object(manager, "on_after_forgot_password", captured),
        patch("app.core.auth.send_password_changed_email", AsyncMock(return_value=True)),
    ):
        await manager.forgot_password(test_user)
        assert captured.await_args is not None
        token = captured.await_args.args[1]
        await manager.reset_password(token, "New-password-123")
    from app.services.mcp_token_service import external_token_status

    assert (
        external_token_status(row, get_jwt_strategy().stamp(test_user), datetime.now(timezone.utc))
        == "credential_changed"
    )


@pytest.mark.asyncio
async def test_recipient_limit_uses_private_key_before_any_lookup(client, monkeypatch, test_user):
    from app.api import password_recovery
    from fastapi import HTTPException
    captured = []
    async def deny(key):
        captured.append(key)
        raise HTTPException(429, 'Too many requests', headers={'Retry-After': '3600'})
    monkeypatch.setattr(password_recovery._recipient_limit, 'check_key', deny)
    deliver = AsyncMock()
    monkeypatch.setattr(password_recovery, '_deliver', deliver)
    for email in (test_user.email, 'unknown@example.com'):
        response = await client.post('/api/auth/forgot-password', json={'email': email})
        assert response.status_code == 429 and response.headers['Retry-After'] == '3600'
    assert all('@' not in key and len(key.rsplit(':', 1)[1]) == 64 for key in captured)
    deliver.assert_not_awaited()


@pytest.mark.asyncio
async def test_unavailable_configuration_does_not_reveal_account(client, monkeypatch, test_user):
    monkeypatch.setattr(get_settings(), 'email_delivery_required', True)
    monkeypatch.setattr(get_settings(), 'smtp_host', '')
    for email in (test_user.email, 'unknown@example.com'):
        response = await client.post('/api/auth/forgot-password', json={'email': email})
        assert response.status_code == 503
        assert email not in response.text


@pytest.mark.asyncio
async def test_reset_preserves_mfa_and_requires_it_on_new_password_login(client, auth_headers, test_user, session):
    import pyotp
    setup = await client.post('/api/auth/2fa/setup', headers=auth_headers)
    assert setup.status_code == 200
    enabled = await client.post('/api/auth/2fa/enable', headers=auth_headers,
                               json={'code': pyotp.TOTP(setup.json()['secret']).now()})
    assert enabled.status_code == 200
    await session.refresh(test_user)
    before = (test_user.totp_secret, test_user.recovery_code_hashes, test_user.auth_epoch)
    captured = AsyncMock(return_value=True)
    with patch('app.api.password_recovery.async_session_maker', TestSessionLocal), patch('app.core.auth.send_password_reset_email', captured), patch('app.core.auth.send_password_changed_email', AsyncMock(return_value=True)):
        assert (await client.post('/api/auth/forgot-password', json={'email': test_user.email})).status_code == 202
        assert captured.await_args is not None
        token = captured.await_args.args[1]
        assert (await client.post('/api/auth/reset-password', json={'token': token, 'password': 'New-password-123'})).status_code == 200
    await session.refresh(test_user)
    assert test_user.is_2fa_enabled
    assert (test_user.totp_secret, test_user.recovery_code_hashes, test_user.auth_epoch) == before
    response = await client.post('/api/auth/login', data={'username': test_user.email, 'password': 'New-password-123'})
    assert response.status_code == 200 and response.json()['requires_2fa'] is True
    assert 'access_token' not in response.json()
