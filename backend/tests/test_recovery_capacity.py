import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi import BackgroundTasks, HTTPException

from app.api import password_recovery
from app.core.recovery_capacity import RecoveryCapacity


@pytest.mark.parametrize("result", [0, 1])
async def test_capacity_is_explicit_and_lease_is_an_opaque_unique_owner(result):
    redis = AsyncMock()
    redis.eval.return_value = result
    capacity = RecoveryCapacity("synthetic:capacity")
    lease = await capacity.acquire(redis)
    assert (lease is None) == (result == 0)
    if lease:
        assert len(lease) >= 32 and "@" not in lease
        await capacity.release(redis, lease)
        await capacity.release(redis, lease)
        assert redis.zrem.await_count == 2
        assert redis.zrem.await_args.args == (capacity.key, lease)


@pytest.mark.parametrize("bad", [None, True, "1", -1, 2])
async def test_invalid_shared_capacity_is_not_treated_as_available(bad):
    redis = AsyncMock()
    redis.eval.return_value = bad
    capacity = RecoveryCapacity("synthetic:capacity")
    with pytest.raises(ValueError):
        await capacity.acquire(redis)
    with pytest.raises(ValueError):
        await capacity.renew(redis, "synthetic-lease")


@pytest.mark.parametrize("outcome", [None, RuntimeError("synthetic private Redis detail")])
async def test_unavailable_capacity_never_queues_mail_or_leaks_details(monkeypatch, outcome):
    monkeypatch.setattr(password_recovery._recipient_limit, "check_key", AsyncMock())
    acquire = AsyncMock(return_value=outcome, side_effect=outcome if isinstance(outcome, Exception) else None)
    monkeypatch.setattr(password_recovery._capacity, "acquire", acquire)
    background = BackgroundTasks()
    with pytest.raises(HTTPException) as exc:
        await password_recovery.queue_account_email(background, "synthetic@example.com", "verify")
    assert exc.value.status_code == 503
    assert exc.value.headers == {"Retry-After": "60"}
    assert "Redis" not in exc.value.detail and "@" not in exc.value.detail
    assert not background.tasks


@pytest.mark.parametrize("renewed", [False, True])
async def test_delayed_expired_mail_is_not_sent_and_only_its_slot_is_released(monkeypatch, renewed):
    renew = AsyncMock(return_value=renewed)
    release = AsyncMock()
    send = AsyncMock()
    monkeypatch.setattr(password_recovery._capacity, "renew", renew)
    monkeypatch.setattr(password_recovery._capacity, "release", release)
    monkeypatch.setattr(password_recovery, "_send_account_email", send)
    await password_recovery._deliver("synthetic@example.com", "verify", "synthetic-lease")
    assert send.await_count == int(renewed)
    assert release.await_args is not None
    assert release.await_args.args[1] == "synthetic-lease"


async def test_stalled_delivery_is_cancelled_and_lease_is_released_without_private_log(monkeypatch, caplog):
    cancelled = asyncio.Event()

    async def stall(*args):
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    release = AsyncMock()
    monkeypatch.setattr(password_recovery._capacity, "renew", AsyncMock(return_value=True))
    monkeypatch.setattr(password_recovery._capacity, "release", release)
    monkeypatch.setattr(password_recovery, "_send_account_email", stall)
    monkeypatch.setattr(password_recovery, "_DELIVERY_TIMEOUT", 0.01)
    await password_recovery._deliver("private@example.com", "reset", "private-lease")
    assert cancelled.is_set() and release.await_count == 1
    assert "private@example.com" not in caplog.text and "private-lease" not in caplog.text
