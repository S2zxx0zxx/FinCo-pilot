"""Real Redis atomic recipient limit; disposable CI-owned key only."""
import asyncio
import os
import uuid

from fastapi import HTTPException
from app.core.rate_limit import RateLimiter
from app.core.redis import get_redis


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
    finally:
        await redis.delete(key)
        await redis.aclose()


if __name__ == '__main__':
    asyncio.run(main())
