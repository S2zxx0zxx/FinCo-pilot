"""CI-only atomic FX quota acceptance against disposable Redis keys."""
import asyncio
import os
import uuid
from typing import Awaitable, cast

from app.core.config import get_settings
from app.core.redis import close_redis, get_redis
from app.services.fx_rate_service import FX_REQUEST_BUDGET_SCRIPT


async def main() -> None:
    if os.environ.get('CI') != 'true' or get_settings().is_production:
        raise RuntimeError('Disposable CI Redis required')
    client = await get_redis()
    prefix = f'finco:ci:fx:{uuid.uuid4()}'
    budget = prefix + ':budget'
    attempts = [prefix + f':attempt:{i}' for i in range(100)]
    try:
        results = await asyncio.gather(*[
            cast(Awaitable[int], client.eval(FX_REQUEST_BUDGET_SCRIPT, 2, key, budget)) for key in attempts
        ])
        assert sum(results) == 24, 'Concurrent daily budget exceeded'
        assert int(await client.get(budget)) == 24
        first = attempts[results.index(1)]
        assert await cast(Awaitable[int], client.eval(FX_REQUEST_BUDGET_SCRIPT, 2, first, budget)) == 0
        assert 0 < await client.ttl(first) <= 3600
        assert 0 < await client.ttl(budget) <= 172800
        print('FX Redis budget: PASS (100 concurrent attempts, 24 reserved; duplicate denied; TTL verified)')
    finally:
        # Only these randomly namespaced disposable acceptance keys are removed.
        await client.delete(budget, *attempts)
        await close_redis()


if __name__ == '__main__':
    asyncio.run(main())
