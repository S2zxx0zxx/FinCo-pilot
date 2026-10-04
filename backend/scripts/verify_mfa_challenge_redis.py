"""CI-only real Redis one-use proof; synthetic identity, no account or email."""
import asyncio
import json
import os
import uuid

from fastapi import HTTPException

from app.core.auth import get_jwt_strategy
from app.core.mfa_challenge import consume_login_challenge
from app.core.redis import close_redis, get_redis
from app.models.user import User


async def main():
    if os.environ.get("CI") != "true":
        raise SystemExit("Refusing proof outside CI")
    client = await get_redis()
    challenge = "ci_challenge_" + uuid.uuid4().hex
    challenge_key = f"2fa_temp:{challenge}"
    nonce_key = "ci_totp_nonce:" + uuid.uuid4().hex
    user = User(id=uuid.uuid4(), email="synthetic@example.com", hashed_password="synthetic", auth_epoch="", is_active=True, is_2fa_enabled=True, totp_secret="synthetic")
    try:
        await client.set(challenge_key, json.dumps({"user_id": str(user.id), "available_methods": ["totp", "passkey"], "credential_stamp": get_jwt_strategy().stamp(user)}), ex=300, nx=True)
        async def attempt(method):
            try:
                await consume_login_challenge(client, challenge, user, method)
                return True
            except HTTPException as exc:
                assert exc.status_code == 401
                return False
        results = await asyncio.gather(*(attempt("totp" if n % 2 else "passkey") for n in range(100)))
        assert sum(results) == 1
        assert await client.get(challenge_key) is None
        nonces = await asyncio.gather(*(client.set(nonce_key, "1", nx=True, ex=120) for _ in range(100)))
        assert sum(result is True for result in nonces) == 1
        assert 0 < await client.ttl(nonce_key) <= 120
        print("PASS: 100 concurrent mixed-factor attempts, one challenge winner; 100 nonce claims, one winner and bounded TTL")
    finally:
        await client.delete(challenge_key, nonce_key)
        await close_redis()


if __name__ == "__main__":
    asyncio.run(main())
