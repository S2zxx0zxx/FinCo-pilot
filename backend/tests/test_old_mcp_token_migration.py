import time
import uuid
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from jose import jwt
from sqlalchemy import func, select

from app.agents.config import get_agent_settings
from app.agents.mcp.auth import JWT_ALGO, JWT_AUDIENCE, JWT_ISSUER
from app.models.mcp_token import ExternalMCPToken
from tests.conftest import TestSessionLocal


@pytest.mark.asyncio
@pytest.mark.parametrize('case', ['unregistered_legacy', 'missing_exp', 'missing_iat', 'missing_aud', 'missing_iss', 'bad_subject', 'bad_workspace', 'bad_jti', 'string_external', 'external_without_registry', 'purpose_conflict', 'string_exp', 'future_iat'])
async def test_ambiguous_legacy_or_malformed_token_rejected_safely(test_user, case):
    from mcp_server.main import app
    now = int(time.time())
    claims = {'sub': str(test_user.id), 'iss': JWT_ISSUER, 'aud': JWT_AUDIENCE, 'iat': now, 'exp': now + 600, 'token_use': 'internal'}
    if case == 'unregistered_legacy':
        claims.pop('token_use')
    elif case.startswith('missing_'):
        claims.pop(case.removeprefix('missing_'))
    elif case == 'bad_subject':
        claims['sub'] = 'not-a-uuid'
    elif case == 'bad_workspace':
        claims['ws_id'] = 'not-a-uuid'
    elif case == 'bad_jti':
        claims.update(ext=True, token_use='external', ws_id=str(uuid.uuid4()), jti='not-a-uuid')
    elif case == 'string_external':
        claims['ext'] = 'false'
    elif case == 'external_without_registry':
        claims.update(ext=True, token_use='external', ws_id=str(uuid.uuid4()))
    elif case == 'purpose_conflict':
        claims['token_use'] = 'external'
    elif case == 'string_exp':
        claims['exp'] = str(now + 600)
    elif case == 'future_iat':
        claims['iat'] = now + 300
    token = jwt.encode(claims, get_agent_settings().mcp_jwt_secret.get_secret_value(), algorithm=JWT_ALGO)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://synthetic') as client:
        response = await client.post('/mcp', headers={'Authorization': 'Bearer ' + token}, json={'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'})
    assert response.status_code == 401
    assert token not in response.text and 'not-a-uuid' not in response.text


@pytest.mark.asyncio
async def test_registered_legacy_token_preserved_and_revocation_denies_discovery(client, auth_headers, test_user):
    from mcp_server.main import app
    minted = (await client.post('/api/agents/mcp-tokens', headers=auth_headers)).json()
    key = get_agent_settings().mcp_jwt_secret.get_secret_value()
    claims = jwt.decode(minted['token'], key, algorithms=[JWT_ALGO], audience=JWT_AUDIENCE, issuer=JWT_ISSUER)
    assert claims.pop('token_use') == 'external'
    legacy = jwt.encode(claims, key, algorithm=JWT_ALGO)
    with patch('mcp_server.main.async_session_maker', TestSessionLocal), patch('app.billing.dependencies.require_workspace_capability', new=AsyncMock()):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://synthetic') as mcp:
            for method in ('initialize', 'tools/list'):
                assert (await mcp.post('/mcp', headers={'Authorization': 'Bearer ' + legacy}, json={'jsonrpc': '2.0', 'id': 1, 'method': method})).status_code == 200
            assert (await client.delete('/api/agents/mcp-tokens/' + minted['id'], headers=auth_headers)).status_code == 204
            response = await mcp.post('/mcp', headers={'Authorization': 'Bearer ' + legacy}, json={'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'})
            assert response.status_code == 403
    rows = (await client.get('/api/agents/mcp-tokens', headers=auth_headers)).json()
    assert rows[0]['status'] == 'revoked' and 'token' not in rows[0]


@pytest.mark.asyncio
@pytest.mark.parametrize('value', ['true', 1, 'false'])
async def test_write_access_requires_real_json_boolean(client, auth_headers, value):
    assert (await client.post('/api/agents/mcp-tokens', headers=auth_headers, json={'allow_writes': value})).status_code == 422


@pytest.mark.asyncio
async def test_failed_signing_does_not_commit_registry_row(client, auth_headers, session):
    before = await session.scalar(select(func.count()).select_from(ExternalMCPToken))
    with patch('app.agents.api.mcp_tokens.mint_token', side_effect=RuntimeError('synthetic signing failure')):
        with pytest.raises(RuntimeError, match='synthetic signing failure'):
            await client.post('/api/agents/mcp-tokens', headers=auth_headers)
    assert await session.scalar(select(func.count()).select_from(ExternalMCPToken)) == before


@pytest.mark.asyncio
async def test_token_inventory_reports_lifecycle_without_exposing_credentials(client, auth_headers, session):
    from datetime import datetime, timedelta, timezone
    minted = [(await client.post('/api/agents/mcp-tokens', headers=auth_headers)).json() for _ in range(4)]
    expired = await session.get(ExternalMCPToken, uuid.UUID(minted[1]['id']))
    expired.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    changed = await session.get(ExternalMCPToken, uuid.UUID(minted[2]['id']))
    changed.credential_stamp = 'invalid-非ascii'
    revoked = await session.get(ExternalMCPToken, uuid.UUID(minted[3]['id']))
    revoked.revoked = True
    await session.commit()
    response = await client.get('/api/agents/mcp-tokens', headers=auth_headers)
    assert response.status_code == 200
    rows = {row['id']: row for row in response.json()}
    assert [rows[row['id']]['status'] for row in minted] == ['active', 'expired', 'credential_changed', 'revoked']
    assert all(row['token'] not in response.text for row in minted)
    assert 'credential_stamp' not in response.text
