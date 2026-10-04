"""Production-safe Redis runtime helpers for FinCo-Pilot.

Roadmap #15 centralizes Redis target validation and client construction so the
FastAPI process, background workers and production acceptance tooling share the
same transport/time-out contract without ever logging connection credentials.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import unquote, urlsplit

import redis.asyncio as redis_async


LOCAL_REDIS_HOSTS = frozenset({
    "localhost",
    "127.0.0.1",
    "::1",
    "redis",
})


@dataclass(frozen=True)
class RedisTarget:
    scheme: str
    hostname: str
    port: int
    database: int
    authenticated: bool

    @property
    def tls(self) -> bool:
        return self.scheme == "rediss"


def parse_redis_target(url: str) -> RedisTarget:
    """Parse a Redis URL without exposing credentials in errors or logs."""
    value = url.strip()
    parsed = urlsplit(value)

    if parsed.scheme not in {"redis", "rediss"}:
        raise ValueError("REDIS_URL must use redis:// or rediss://")
    if not parsed.hostname:
        raise ValueError("REDIS_URL must include a hostname")

    try:
        port = parsed.port or 6379
    except ValueError as exc:
        raise ValueError("REDIS_URL contains an invalid port") from exc

    path = parsed.path.strip("/")
    if path:
        if not path.isdigit():
            raise ValueError("REDIS_URL database path must be a non-negative integer")
        database = int(path)
    else:
        database = 0

    if database < 0:
        raise ValueError("REDIS_URL database index must be non-negative")

    authenticated = bool(parsed.password and unquote(parsed.password).strip())

    return RedisTarget(
        scheme=parsed.scheme,
        hostname=parsed.hostname.lower(),
        port=port,
        database=database,
        authenticated=authenticated,
    )


def validate_redis_target(
    url: str,
    *,
    external_required: bool,
    tls_required: bool,
    auth_required: bool,
) -> RedisTarget:
    target = parse_redis_target(url)

    if external_required:
        bundled_host = (
            target.hostname in LOCAL_REDIS_HOSTS
            or target.hostname.endswith("-redis-master")
        )
        if bundled_host:
            raise ValueError(
                "REDIS_EXTERNAL_REQUIRED=true requires an external Redis host"
            )

    if tls_required and not target.tls:
        raise ValueError("REDIS_TLS_REQUIRED=true requires REDIS_URL to use rediss://")

    if auth_required and not target.authenticated:
        raise ValueError(
            "REDIS_AUTH_REQUIRED=true requires authenticated REDIS_URL credentials"
        )

    return target


def create_async_redis_client(
    url: str,
    *,
    max_connections: int,
    socket_connect_timeout_seconds: int,
    socket_timeout_seconds: int,
    health_check_interval_seconds: int,
    ssl_ca_file: str = "",
    client_name: str = "fincopilot",
) -> redis_async.Redis:
    """Create a bounded async Redis client.

    TLS is selected by the URL scheme. A custom CA is optional for private
    managed Redis endpoints; public managed services normally need no CA file.
    """
    target = parse_redis_target(url)
    kwargs: dict[str, object] = {
        "decode_responses": True,
        "max_connections": max_connections,
        "socket_connect_timeout": socket_connect_timeout_seconds,
        "socket_timeout": socket_timeout_seconds,
        "health_check_interval": health_check_interval_seconds,
        "client_name": client_name,
    }
    if target.tls and ssl_ca_file.strip():
        kwargs["ssl_ca_certs"] = ssl_ca_file.strip()

    return redis_async.from_url(url, **kwargs)


async def redis_roundtrip(client: redis_async.Redis, key: str) -> None:
    """Credential-safe ping + ephemeral write/read/delete acceptance check."""
    await client.ping()
    created = await client.set(key, "ok", ex=30, nx=True)
    if not created:
        raise RuntimeError("Redis acceptance key unexpectedly already exists")
    try:
        value = await client.get(key)
        if value != "ok":
            raise RuntimeError("Redis write/read round-trip returned an unexpected value")
        ttl = await client.ttl(key)
        if ttl <= 0 or ttl > 30:
            raise RuntimeError("Redis acceptance key TTL is outside the expected bound")
    finally:
        await client.delete(key)
