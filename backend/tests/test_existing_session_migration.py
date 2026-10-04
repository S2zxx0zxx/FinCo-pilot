"""Real API acceptance matrix for legacy/current sessions; no token grace bypass."""
import time

import jwt
import pytest
from pydantic import SecretStr

from app.core.auth import get_jwt_strategy


@pytest.mark.asyncio
@pytest.mark.parametrize('case', ['legacy', 'missing_exp', 'missing_aud', 'wrong_aud', 'expired', 'unicode_stamp', 'wrong_stamp', 'wrong_signature', 'wrong_algorithm', 'string_expiry', 'infinite_expiry'])
async def test_untrusted_old_or_malformed_session_requires_login(client, test_user, case):
    strategy = get_jwt_strategy()
    claims = {'sub': str(test_user.id), 'aud': strategy.token_audience, 'exp': int(time.time()) + 600, 'credential_stamp': strategy.stamp(test_user)}
    key, algorithm = strategy.secret.get_secret_value() if isinstance(strategy.secret, SecretStr) else str(strategy.secret), strategy.algorithm
    if case == 'legacy':
        claims.pop('credential_stamp')
    elif case == 'missing_exp':
        claims.pop('exp')
    elif case == 'missing_aud':
        claims.pop('aud')
    elif case == 'wrong_aud':
        claims['aud'] = ['fastapi-users:reset']
    elif case == 'expired':
        claims['exp'] = int(time.time()) - 60
    elif case == 'unicode_stamp':
        claims['credential_stamp'] = 'é' * 64
    elif case == 'wrong_stamp':
        claims['credential_stamp'] = '0' * 64
    elif case == 'wrong_signature':
        key = 'synthetic-untrusted-key-not-for-production-1234567890'
    elif case == 'wrong_algorithm':
        algorithm = 'HS384'
        key = 'synthetic-wrong-algorithm-key-not-for-production-1234567890123456789'
    elif case == 'string_expiry':
        claims['exp'] = str(int(time.time()) + 600)
    elif case == 'infinite_expiry':
        claims['exp'] = float('inf')
    token = jwt.encode(claims, key, algorithm=algorithm)
    response = await client.get('/api/users/me', headers={'Authorization': 'Bearer ' + token})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_current_sessions_survive_empty_epoch_migration_but_logout_revokes_all(client, test_user, session):
    strategy = get_jwt_strategy()
    assert not test_user.auth_epoch
    first, second = await strategy.write_token(test_user), await strategy.write_token(test_user)
    headers = {'Authorization': 'Bearer ' + first}
    assert (await client.get('/api/users/me', headers=headers)).status_code == 200
    assert (await client.post('/api/auth/logout', headers=headers)).status_code == 200
    for token in (first, second):
        assert (await client.get('/api/users/me', headers={'Authorization': 'Bearer ' + token})).status_code == 401
    await session.refresh(test_user)
    replacement = await strategy.write_token(test_user)
    assert (await client.get('/api/users/me', headers={'Authorization': 'Bearer ' + replacement})).status_code == 200
