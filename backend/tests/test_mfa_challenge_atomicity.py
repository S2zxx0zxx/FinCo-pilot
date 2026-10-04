import asyncio
import json
import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.core.auth import get_jwt_strategy
from app.core.mfa_challenge import consume_login_challenge
from app.models.user import User


def user_and_payload():
    user = User(id=uuid.uuid4(), email="synthetic@example.com", hashed_password="synthetic", auth_epoch="", is_active=True, is_2fa_enabled=True, totp_secret="synthetic")
    payload = {"user_id": str(user.id), "available_methods": ["totp", "passkey"], "credential_stamp": get_jwt_strategy().stamp(user)}
    return user, payload


@pytest.mark.asyncio
async def test_concurrent_factor_methods_only_one_challenge_winner():
    user, payload = user_and_payload()
    store = {"2fa_temp:challenge": json.dumps(payload)}
    redis = AsyncMock()
    async def getdel(key):
        return store.pop(key, None)
    redis.getdel.side_effect = getdel
    results = await asyncio.gather(*(consume_login_challenge(redis, "challenge", user, method) for method in ("totp", "passkey")), return_exceptions=True)
    assert sum(result is None for result in results) == 1
    rejected = next(result for result in results if result is not None)
    assert isinstance(rejected, HTTPException) and rejected.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["missing", "malformed", "wrong_user", "wrong_method", "changed_password", "disabled_factor"])
async def test_consumption_rejects_stale_or_untrusted_payload(change):
    user, payload = user_and_payload()
    if change == "wrong_user":
        payload["user_id"] = str(uuid.uuid4())
    elif change == "wrong_method":
        payload["available_methods"] = ["passkey"]
    elif change == "changed_password":
        user.hashed_password = "new-password-hash"
    elif change == "disabled_factor":
        user.is_2fa_enabled = False
    raw = None if change == "missing" else (b"\xff" if change == "malformed" else json.dumps(payload))
    redis = AsyncMock()
    redis.getdel.return_value = raw
    with pytest.raises(HTTPException) as caught:
        await consume_login_challenge(redis, "challenge", user, "totp")
    assert caught.value.status_code == 401


@pytest.mark.asyncio
async def test_redis_outage_fails_closed_without_raw_error():
    user, _ = user_and_payload()
    redis = AsyncMock()
    redis.getdel.side_effect = RuntimeError("synthetic secret-bearing connection URL")
    with pytest.raises(HTTPException) as caught:
        await consume_login_challenge(redis, "challenge", user, "totp")
    assert caught.value.status_code == 503
    assert "secret" not in caught.value.detail
