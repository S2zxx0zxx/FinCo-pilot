"""Credential-safe production Redis + Celery acceptance probe.

Never prints REDIS_URL, credentials, task ids, values from the secret store, or
provider response bodies.
"""
from __future__ import annotations

import argparse
import asyncio
import secrets
import sys

from app.core.config import get_settings
from app.core.redis_runtime import create_async_redis_client, redis_roundtrip


async def _verify_redis() -> None:
    settings = get_settings()
    client = create_async_redis_client(
        settings.redis_url,
        max_connections=min(settings.redis_max_connections, 5),
        socket_connect_timeout_seconds=settings.redis_socket_connect_timeout_seconds,
        socket_timeout_seconds=settings.redis_socket_timeout_seconds,
        health_check_interval_seconds=settings.redis_health_check_interval_seconds,
        ssl_ca_file=settings.redis_ssl_ca_file,
        client_name="fincopilot-redis-acceptance",
    )
    key = "fincopilot:acceptance:" + secrets.token_hex(12)
    try:
        await redis_roundtrip(client, key)
    finally:
        await client.aclose()


def _verify_worker() -> None:
    from app.worker import celery_app

    nonce = secrets.token_hex(12)
    result = celery_app.send_task("app.worker.health_probe", args=[nonce])
    try:
        payload = result.get(timeout=20)
        if payload != {"ok": True, "nonce": nonce}:
            raise RuntimeError("Celery health probe returned an unexpected payload")
    finally:
        result.forget()


def _verify_schedule() -> None:
    from app.worker import celery_app

    schedule = celery_app.conf.beat_schedule
    required = {
        "sync-all-connections-hourly",
        "generate-recurring-daily",
        "apply-asset-growth-daily",
        "refresh-market-prices-daily",
        "sync-fx-rates-daily",
        "restamp-recurring-fx-daily",
        "restamp-fallback-fx-daily",
    }
    missing = sorted(required.difference(schedule))
    if missing:
        raise RuntimeError("Celery Beat schedule is incomplete")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ci",
        action="store_true",
        help="allow the disposable CI/development environment",
    )
    parser.add_argument(
        "--redis-only",
        action="store_true",
        help="verify Redis transport only; used before the API process starts",
    )
    parser.add_argument(
        "--require-worker",
        action="store_true",
        help="also require a live worker broker/result round-trip",
    )
    args = parser.parse_args()

    settings = get_settings()
    if not args.ci and not settings.is_production:
        print("Refusing live Redis acceptance outside production; use --ci only in disposable CI.")
        return 2

    try:
        asyncio.run(_verify_redis())
        print("Redis ping/write/read/TTL/delete round-trip: OK")

        if not args.redis_only:
            _verify_schedule()
            print("Celery Beat static schedule contract: OK")

        if args.require_worker:
            _verify_worker()
            print("Celery broker/worker/result-backend round-trip: OK")
    except Exception as exc:  # noqa: BLE001 - intentionally sanitize provider errors
        print(f"Redis/worker acceptance failed: {type(exc).__name__}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
