"""Atomic, expiring mail-task leases shared by every API worker."""

import secrets
from typing import Awaitable, cast

from redis.asyncio import Redis


ACQUIRE = """
local clock = redis.call('TIME')
local now = tonumber(clock[1]) + tonumber(clock[2]) / 1000000
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now)
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[2]) then return 0 end
local added = redis.call('ZADD', KEYS[1], 'NX', now + tonumber(ARGV[3]), ARGV[1])
if added == 1 then redis.call('EXPIRE', KEYS[1], ARGV[3]) end
return added
"""

RENEW = """
local clock = redis.call('TIME')
local now = tonumber(clock[1]) + tonumber(clock[2]) / 1000000
local deadline = redis.call('ZSCORE', KEYS[1], ARGV[1])
if not deadline or tonumber(deadline) <= now then return 0 end
redis.call('ZADD', KEYS[1], 'XX', now + tonumber(ARGV[2]), ARGV[1])
redis.call('EXPIRE', KEYS[1], ARGV[2])
return 1
"""


class RecoveryCapacity:
    def __init__(self, key: str, limit: int = 8, ttl: int = 120):
        self.key = key
        self.limit = limit
        self.ttl = ttl

    async def acquire(self, redis: Redis) -> str | None:
        lease = secrets.token_urlsafe(32)
        # redis-py's shared command stub also describes the synchronous client;
        # this parameter is specifically redis.asyncio.Redis.
        result = await cast(Awaitable[object], redis.eval(ACQUIRE, 1, self.key, lease, str(self.limit), str(self.ttl)))
        if type(result) is not int or result not in {0, 1}:
            raise ValueError("Invalid recovery capacity response")
        return lease if result else None

    async def renew(self, redis: Redis, lease: str) -> bool:
        result = await cast(Awaitable[object], redis.eval(RENEW, 1, self.key, lease, str(self.ttl)))
        if type(result) is not int or result not in {0, 1}:
            raise ValueError("Invalid recovery capacity response")
        return bool(result)

    async def release(self, redis: Redis, lease: str) -> None:
        # Idempotent ownership-based removal. An expired task cannot decrement
        # a replacement task's slot or manufacture negative capacity.
        await redis.zrem(self.key, lease)
