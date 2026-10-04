"""Native concurrent durable receipt proof, restricted to disposable CI PostgreSQL."""
import asyncio
import json
import hmac
import hashlib
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
import os
from pathlib import Path
from unittest.mock import patch
import uuid

from sqlalchemy import delete, func, select, text

from app.billing.webhook_inbox import decrypt_snapshot, persist_webhook
from app.core.database import async_session_maker, engine
from app.core.config import get_settings
from app.main import app
from app.models.payment_webhook import PaymentWebhookEvent


async def main():
    if os.environ.get("FINCO_DISPOSABLE_DB_TEST") != "yes" or os.environ.get("CI") != "true":
        raise SystemExit("Refusing proof outside disposable CI database")
    if engine.dialect.name != "postgresql":
        raise SystemExit("Native PostgreSQL required")
    account = "acc_CI" + uuid.uuid4().hex
    event = {"entity": "event", "account_id": account, "event": "payment.captured",
             "created_at": 1, "payload": {"payment": {"entity": {"id": "pay_CISynthetic", "entity": "payment",
             "amount": 1900, "currency": "INR", "email": "private-ci-canary@example.com"}}}}
    body = json.dumps(event).encode()
    settings = get_settings()
    secret = "synthetic-ci-webhook-signing-key-0123456789"
    previous = {key: getattr(settings, key) for key in (
        "razorpay_webhook_enabled", "razorpay_webhook_secret", "razorpay_webhook_account_id", "razorpay_webhook_mode")}
    settings.razorpay_webhook_enabled = True
    settings.razorpay_webhook_secret = SecretStr(secret)
    settings.razorpay_webhook_account_id = account

    async def receive(hint, raw=body, mode="test"):
        settings.razorpay_webhook_mode = mode
        signature = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://synthetic-ci") as client:
            response = await client.post("/api/webhooks/razorpay", content=raw, headers={
                "content-type": "application/json", "x-razorpay-signature": signature,
                "x-razorpay-event-id": hint})
            assert response.status_code == 200, response.status_code
            assert response.headers["cache-control"] == "no-store"

    try:
        # A unique-index loser cannot acknowledge before the winner commits.
        winner_ready = asyncio.Event()
        release_winner = asyncio.Event()
        async with async_session_maker() as winner:
            original_commit = winner.commit

            async def held_commit():
                winner_ready.set()
                await release_winner.wait()
                await original_commit()

            with patch.object(winner, "commit", held_commit):
                first = asyncio.create_task(persist_webhook(winner, body=body, event=event,
                                                           delivery_id="evt_Winner", mode="test"))
                second = None
                try:
                    await asyncio.wait_for(winner_ready.wait(), 3)
                    second = asyncio.create_task(receive("evt_Substituted"))
                    await asyncio.sleep(0.05)
                    assert not second.done(), "duplicate was acknowledged before winner commit"
                finally:
                    release_winner.set()
                    await asyncio.wait_for(asyncio.gather(first, *([second] if second else [])), 5)
        await asyncio.gather(*(receive("evt_Retry" + str(i)) for i in range(12)))
        async with async_session_maker() as session:
            count = await session.scalar(select(func.count()).select_from(PaymentWebhookEvent).where(PaymentWebhookEvent.account_id == account))
            assert count == 1
            row = await session.scalar(select(PaymentWebhookEvent).where(PaymentWebhookEvent.account_id == account))
            assert row and decrypt_snapshot(row)["payload"]["payment"]["entity"]["amount"] == 1900
            assert "private-ci-canary" not in row.snapshot_ciphertext
        other = {**event, "created_at": 2}
        await receive("evt_Winner", json.dumps(other).encode())
        await receive("evt_Winner", mode="live")
        async with async_session_maker() as session:
            assert await session.scalar(select(func.count()).select_from(PaymentWebhookEvent).where(PaymentWebhookEvent.account_id == account)) == 3
            # An acknowledged record makes migration downgrade fail closed.
            import importlib.util
            from alembic.migration import MigrationContext
            from alembic.operations import Operations
            spec = importlib.util.spec_from_file_location("webhook102", Path(__file__).resolve().parents[1] / "alembic/versions/102_payment_webhook_events.py")
            assert spec and spec.loader
            migration = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(migration)
            connection = await session.connection()

            def downgrade_proof(sync_connection):
                with Operations.context(MigrationContext.configure(sync_connection)):
                    try:
                        migration.downgrade()
                    except RuntimeError:
                        return
                    raise AssertionError("Acknowledged receipts were destroyed")

            await connection.run_sync(downgrade_proof)
            assert await session.scalar(text("SELECT count(*) FROM payment_webhook_events WHERE account_id=:account"), {"account": account}) == 3
        print("PASS: native PostgreSQL full signed HTTP receipt pipeline commit once; loser waits for commit; unsigned-header substitution cannot duplicate/poison; mode isolation and encrypted minimized snapshot verified; populated downgrade refuses evidence loss")
    finally:
        async with async_session_maker() as session:
            await session.execute(delete(PaymentWebhookEvent).where(PaymentWebhookEvent.account_id == account))
            await session.commit()
        for key, value in previous.items():
            setattr(settings, key, value)
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
