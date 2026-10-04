import time
import uuid
import jwt
import pytest
from fastapi_users.jwt import generate_jwt
from app.core.auth import get_jwt_strategy
from app.core.config import get_settings
from app.models.account_deletion import AccountDeletion


@pytest.mark.asyncio
async def test_request_requires_fresh_auth_confirmation_and_secret_receipt(client, auth_headers, session, test_user):
    assert (await client.post('/api/account-deletion', headers=auth_headers, json={'confirmation': 'wrong'})).status_code == 422
    response = await client.post('/api/account-deletion', headers=auth_headers, json={'confirmation': 'DELETE MY ACCOUNT'})
    assert response.status_code == 202
    data = response.json()
    assert len(data['tracking_token']) >= 32
    identity = data['id']
    assert (await client.get(f'/api/account-deletion/{identity}/status')).status_code == 404
    assert (await client.get(f'/api/account-deletion/{identity}/status', headers={'X-Deletion-Receipt': 'x'*43})).status_code == 404
    status = await client.get(f'/api/account-deletion/{identity}/status', headers={'X-Deletion-Receipt': data['tracking_token']})
    assert status.status_code == 200 and status.headers['cache-control'] == 'no-store'
    assert not {'manifest', 'tracking_token', 'tracking_digest', 'user_id'} & set(status.json())
    assert (await client.post('/api/account-deletion', headers=auth_headers, json={'confirmation': 'DELETE MY ACCOUNT'})).status_code == 409
    assert (await client.post(f'/api/account-deletion/{identity}/cancel', headers=auth_headers)).status_code == 200
    assert (await session.get(AccountDeletion, uuid.UUID(identity))).active_user_id is None
    assert (await client.post('/api/account-deletion', headers=auth_headers, json={'confirmation': 'DELETE MY ACCOUNT'})).status_code == 202


@pytest.mark.asyncio
@pytest.mark.parametrize('stamp_time', [None, True, 'stale', 'future'])
async def test_legacy_stale_and_future_auth_denied(client, test_user, stamp_time):
    strategy = get_jwt_strategy()
    if stamp_time == 'stale':
        stamp_time = int(time.time()) - 360
    elif stamp_time == 'future':
        stamp_time = int(time.time()) + 60
    payload = {'sub': str(test_user.id), 'aud': strategy.token_audience, 'credential_stamp': strategy.stamp(test_user)}
    if stamp_time is not None:
        payload['auth_time'] = stamp_time
    token = generate_jwt(payload, strategy.encode_key, strategy.lifetime_seconds, algorithm=strategy.algorithm)
    response = await client.post('/api/account-deletion', headers={'Authorization': f'Bearer {token}'}, json={'confirmation': 'DELETE MY ACCOUNT'})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_operator_not_granted_by_user_token(client, auth_headers, test_user):
    for method, path, body in [('get', '/api/account-deletion/operator/requests', None), ('post', '/api/account-deletion/operator/holds', {'user_id': str(test_user.id), 'reason': 'legal', 'evidence_sha256': 'a'*64})]:
        response = await getattr(client, method)(path, headers=auth_headers, **({'json': body} if body else {}))
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_fresh_auth_claim_issued_only_after_full_login(client, auth_headers, test_user):
    strategy = get_jwt_strategy()
    legacy = await strategy.write_token(test_user)
    data = jwt.decode(legacy, get_settings().secret_key.get_secret_value(), algorithms=[strategy.algorithm], audience=strategy.token_audience)
    assert 'auth_time' not in data
    fresh = auth_headers['Authorization'].split(' ')[1]
    data = jwt.decode(fresh, get_settings().secret_key.get_secret_value(), algorithms=[strategy.algorithm], audience=strategy.token_audience)
    assert type(data['auth_time']) is int


@pytest.mark.asyncio
async def test_execution_revokes_sessions_but_secret_receipt_still_works(client, auth_headers, session, test_user, test_superuser):
    from app.services import account_deletion_service as service
    response = await client.post('/api/account-deletion', headers=auth_headers, json={'confirmation': 'DELETE MY ACCOUNT'})
    data = response.json()
    job = await session.get(AccountDeletion, uuid.UUID(data['id']))
    await service.review_deletion(session, job, test_superuser, 'a'*64)
    for required in job.manifest['requirements']:
        await service.record_receipt(session, job, test_superuser, required, 'b'*64)
    await service.execute_deletion(session, job, str(test_superuser.id))
    assert (await client.get('/api/users/me', headers=auth_headers)).status_code == 401
    assert (await client.post(f"/api/account-deletion/{data['id']}/cancel", headers=auth_headers)).status_code == 401
    tracked = await client.get(f"/api/account-deletion/{data['id']}/status", headers={'X-Deletion-Receipt': data['tracking_token']})
    assert tracked.status_code == 200 and tracked.json()['state'] == 'backup_expiry_pending'
