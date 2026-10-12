"""Real Redis atomic recipient limit; disposable CI-owned key only."""
import asyncio
import os
import uuid

from fastapi import HTTPException
from app.core.rate_limit import RateLimiter
from app.core.redis import get_redis
from app.core.recovery_capacity import RecoveryCapacity
from app.api.oidc_auth import _consume_oidc_state


async def verify_oidc_state(redis, state):
    key = 'oidc_state:' + state
    original = '{"nonce":"synthetic-ci-nonce","code_verifier":"synthetic-ci-verifier"}'
    try:
        await redis.set(key, original, ex=600)
        results = await asyncio.wait_for(asyncio.gather(*(_consume_oidc_state(redis, state) for _ in range(32))), 15)
        assert len([result for result in results if result is not None]) == 1
        assert await redis.get(key) is None
        assert await _consume_oidc_state(redis, state) is None
        print('PASS: 32 native Redis OIDC state consumers yield exactly one winner; replay refused')
    finally:
        await redis.delete(key)


async def verify_capacity(redis, key):
    slots = RecoveryCapacity(key, limit=8, ttl=120)
    try:
        leases = await asyncio.wait_for(asyncio.gather(*(slots.acquire(redis) for _ in range(32))), 15)
        accepted = [lease for lease in leases if lease is not None]
        assert len(accepted) == 8 and len(set(accepted)) == 8
        assert await redis.zcard(key) == 8 and await redis.ttl(key) > 0
        await slots.release(redis, accepted[0])
        await slots.release(redis, accepted[0])
        assert await redis.zcard(key) == 7
        replacement = await slots.acquire(redis)
        assert replacement is not None and replacement not in accepted
        await slots.release(redis, accepted[0])
        assert await redis.zcard(key) == 8
        # Simulate a crashed task's expired lease without sleeping or changing
        # Redis's clock. Only the random disposable CI key is changed.
        await redis.zadd(key, {accepted[1]: 0})
        assert not await slots.renew(redis, accepted[1])
        recovered = await slots.acquire(redis)
        assert recovered is not None and await redis.zcard(key) == 8
        await slots.release(redis, accepted[1])
        assert await redis.zcard(key) == 8
        assert await slots.renew(redis, recovered)
        print('PASS: 32 concurrent mail leases allowed exactly 8; expiry and stale/double release preserve replacements')
    finally:
        await redis.delete(key)


async def main():
    if os.environ.get('CI') != 'true':
        raise SystemExit('Refusing outside disposable CI')
    redis = await get_redis()
    key = 'ci:password-recovery:' + uuid.uuid4().hex
    limiter = RateLimiter(max_requests=3, window_seconds=3600)
    try:
        async def attempt():
            try:
                await limiter.check_key(key)
                return 'allowed'
            except HTTPException as exc:
                assert exc.status_code == 429
                return 'limited'
        results = await asyncio.wait_for(asyncio.gather(*(attempt() for _ in range(20))), 15)
        assert results.count('allowed') == 3 and results.count('limited') == 17, results
        assert await redis.ttl(key) > 0
        print('PASS: 20 concurrent Redis attempts allowed exactly 3 and retained bounded TTL')
        await verify_capacity(redis, key + ':mail-leases')
        await verify_oidc_state(redis, key + ':oidc')
    finally:
        await redis.delete(key)
        await redis.aclose()


if __name__ == '__main__':
    asyncio.run(main())
