"""Regression cases reproduced by the September launch audit."""
from unittest.mock import patch

import httpx
import pyotp
import pytest
from sqlalchemy import select

from app.models.category import Category
from app.models.workspace import WorkspaceMember


@pytest.mark.asyncio
async def test_short_password_rejected_server_side(client, clean_db):
    response = await client.post('/api/auth/register', json={'email': 'weak@example.com', 'password': 'x'})
    assert response.status_code == 400
    assert response.json()['detail']['code'] == 'REGISTER_INVALID_PASSWORD'


@pytest.mark.asyncio
async def test_logout_invalidates_copied_token(client, auth_headers):
    assert (await client.post('/api/auth/logout', headers=auth_headers)).status_code == 200
    assert (await client.get('/api/users/me', headers=auth_headers)).status_code == 401


@pytest.mark.asyncio
async def test_password_change_invalidates_old_token(client, auth_headers):
    response = await client.patch('/api/users/me', headers=auth_headers, json={'password': 'new-safe-pass-123'})
    assert response.status_code == 200
    assert (await client.get('/api/users/me', headers=auth_headers)).status_code == 401
    login = await client.post('/api/auth/login', data={'username': 'test@example.com', 'password': 'new-safe-pass-123'})
    assert login.status_code == 200
    assert (await client.get('/api/users/me', headers={'Authorization': 'Bearer ' + login.json()['access_token']})).status_code == 200


@pytest.mark.asyncio
async def test_enabled_totp_cannot_be_replaced(client, auth_headers, test_user, session):
    test_user.is_2fa_enabled = True
    test_user.totp_secret = pyotp.random_base32()
    old = test_user.totp_secret
    await session.commit()
    assert (await client.post('/api/auth/2fa/setup', headers=auth_headers)).status_code == 409
    await session.refresh(test_user)
    assert test_user.totp_secret == old


@pytest.mark.asyncio
async def test_recovery_code_is_one_use(client, auth_headers, test_user):
    from tests.test_two_factor import _make_redis_mock_with_store
    redis = _make_redis_mock_with_store()
    setup = (await client.post('/api/auth/2fa/setup', headers=auth_headers)).json()
    enabled = await client.post('/api/auth/2fa/enable', headers=auth_headers, json={'code': pyotp.TOTP(setup['secret']).now()})
    codes = enabled.json()['recovery_codes']
    assert len(codes) == len(set(codes)) == 10
    assert (await client.post('/api/auth/2fa/enable', headers=auth_headers, json={'code': pyotp.TOTP(setup['secret']).now()})).status_code == 409
    with patch('app.api.custom_auth.get_redis', return_value=redis), patch('app.api.two_factor.get_redis', return_value=redis):
        for expected in (200, 400):
            challenge = await client.post('/api/auth/login', data={'username': test_user.email, 'password': 'testpass123'})
            assert challenge.status_code == 200
            payload = {'temp_token': challenge.json()['temp_token'], 'code': codes[0]}
            assert (await client.post('/api/auth/2fa/verify', json=payload)).status_code == expected


@pytest.mark.asyncio
async def test_verify_routes_mounted(client):
    assert (await client.post('/api/auth/verify', json={'token': 'invalid'})).status_code == 400


@pytest.mark.asyncio
async def test_invalid_account_and_dates_rejected(client, auth_headers, test_account):
    invalid = await client.post('/api/accounts', headers=auth_headers, json={'name': ' ', 'type': 'invalid', 'currency': 'NOTACURRENCY', 'statement_close_day': 99})
    assert invalid.status_code == 422
    assert (await client.get(f'/api/accounts/{test_account.id}/summary?from=bad-date', headers=auth_headers)).status_code == 422


@pytest.mark.asyncio
async def test_negative_debit_rejected(client, auth_headers, test_account):
    response = await client.post('/api/transactions', headers=auth_headers, json={'account_id': str(test_account.id), 'description': 'Expense', 'amount': '-1500', 'type': 'debit', 'date': '2026-09-19'})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_external_mcp_permission_and_revocation(client, auth_headers, test_user, test_workspace, session):
    from tests.conftest import TestSessionLocal
    import mcp_server.main as mcp
    minted = await client.post('/api/agents/mcp-tokens', headers=auth_headers)
    assert minted.status_code == 201
    row = minted.json()
    async def call(token, name='Audit denied category', apply=True):
        with patch.object(mcp, 'async_session_maker', TestSessionLocal):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=mcp.app), base_url='http://mcp') as mc:
                response = await mc.post('/mcp', headers={'Authorization': 'Bearer ' + token}, json={'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {'name': 'propose_create_category', 'arguments': {'name': name, 'apply': apply}}})
                return response.json()['result']
    assert (await call(row['token']))['isError'] is True  # read-only by default
    for invalid in ('true', 1, [True]):
        assert (await call(row['token'], apply=invalid))['isError'] is True
    writer = (await client.post('/api/agents/mcp-tokens', headers=auth_headers, json={'allow_writes': True})).json()
    proposed = (await call(writer['token'], 'Audit allowed category'))['structuredContent']
    assert proposed['applied'] is False
    assert proposed['requires_approval'] is True
    assert (await session.execute(select(Category).where(Category.name == 'Audit allowed category'))).first() is None
    approve_path = '/api/agents/mcp-tokens/approvals/' + proposed['approval_id'] + '/approve'
    approved = await client.post(approve_path, headers=auth_headers)
    assert approved.status_code == 200, approved.text
    assert approved.json()['result']['applied'] is True
    assert (await client.post(approve_path, headers=auth_headers)).status_code == 409
    denied = (await call(writer['token'], 'Audit denied category'))['structuredContent']
    reject_path = '/api/agents/mcp-tokens/approvals/' + denied['approval_id']
    assert (await client.post(reject_path + '/reject', headers=auth_headers)).status_code == 200
    assert (await client.post(reject_path + '/approve', headers=auth_headers)).status_code == 409
    revoked_pending = (await call(writer['token'], 'Audit denied category'))['structuredContent']
    assert (await client.delete('/api/agents/mcp-tokens/' + writer['id'], headers=auth_headers)).status_code == 204
    assert (await call(writer['token']))['isError'] is True
    assert (await client.post('/api/agents/mcp-tokens/approvals/' + revoked_pending['approval_id'] + '/approve', headers=auth_headers)).status_code == 409
    writer = (await client.post('/api/agents/mcp-tokens', headers=auth_headers, json={'allow_writes': True})).json()
    pending_before_downgrade = (await call(writer['token']))['structuredContent']
    member = (await session.execute(select(WorkspaceMember).where(WorkspaceMember.user_id == test_user.id, WorkspaceMember.workspace_id == test_workspace.id))).scalar_one()
    member.role = 'viewer'
    await session.commit()
    assert (await client.post('/api/agents/mcp-tokens/approvals/' + pending_before_downgrade['approval_id'] + '/approve', headers=auth_headers)).status_code == 403
    assert (await call(writer['token']))['isError'] is True
    await session.delete(member)
    await session.commit()
    assert (await call(writer['token']))['isError'] is True
    assert (await session.execute(select(Category).where(Category.name == 'Audit denied category'))).first() is None


@pytest.mark.asyncio
async def test_metrics_require_credential(client, monkeypatch):
    from app.core.config import get_settings
    from pydantic import SecretStr
    monkeypatch.setattr(get_settings(), 'metrics_enabled', True)
    monkeypatch.setattr(get_settings(), 'metrics_token', SecretStr('synthetic-metrics-key'))
    assert (await client.get('/metrics')).status_code == 401
    response = await client.get('/metrics', headers={'Authorization': 'Bearer synthetic-metrics-key'})
    assert response.status_code == 200
    assert 'finco_process_uptime_seconds' in response.text
    assert 'test@example.com' not in response.text


@pytest.mark.asyncio
async def test_password_change_invalidates_pending_second_factor(client, auth_headers, test_user, session):
    from tests.test_two_factor import _make_redis_mock_with_store
    redis = _make_redis_mock_with_store()
    test_user.is_2fa_enabled = True
    test_user.totp_secret = pyotp.random_base32()
    await session.commit()
    with patch('app.api.custom_auth.get_redis', return_value=redis), patch('app.api.two_factor.get_redis', return_value=redis):
        challenge = await client.post('/api/auth/login', data={'username': test_user.email, 'password': 'testpass123'})
        assert challenge.status_code == 200
        changed = await client.patch('/api/users/me', headers=auth_headers, json={'password': 'Changed-password-123'})
        assert changed.status_code == 200
        response = await client.post('/api/auth/2fa/verify', json={'temp_token': challenge.json()['temp_token'], 'code': pyotp.TOTP(test_user.totp_secret).now()})
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_lost_authenticator_can_be_replaced_with_password_and_unused_recovery_code(client, auth_headers, test_user, session):
    setup = (await client.post('/api/auth/2fa/setup', headers=auth_headers)).json()
    enabled = (await client.post('/api/auth/2fa/enable', headers=auth_headers, json={'code': pyotp.TOTP(setup['secret']).now()})).json()
    code = enabled['recovery_codes'][0]
    assert (await client.post('/api/auth/2fa/disable', headers=auth_headers, json={'password': 'wrong-password', 'code': code})).status_code == 400
    # Wrong password must not consume the code.
    disabled = await client.post('/api/auth/2fa/disable', headers=auth_headers, json={'password': 'testpass123', 'code': code})
    assert disabled.status_code == 200
    await session.refresh(test_user)
    assert test_user.is_2fa_enabled is False
    assert test_user.totp_secret is None
    assert test_user.recovery_code_hashes == []
    replacement = (await client.post('/api/auth/2fa/setup', headers=auth_headers)).json()
    assert replacement['secret'] != setup['secret']
    response = await client.post('/api/auth/2fa/enable', headers=auth_headers, json={'code': pyotp.TOTP(replacement['secret']).now()})
    assert response.status_code == 200
    assert set(response.json()['recovery_codes']).isdisjoint(enabled['recovery_codes'])
    # An old recovery code never disables the newly enrolled authenticator.
    assert (await client.post('/api/auth/2fa/disable', headers=auth_headers, json={'password': 'testpass123', 'code': code})).status_code == 400
