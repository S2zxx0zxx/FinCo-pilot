"""Bounded durable inbox polling; no reliance on a webhook-to-broker enqueue."""
import asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker
from app.billing.activation import activation_enabled, scan_receipts
from app.core.config import get_settings
from app.core.database_runtime import create_database_engine
from app.worker import celery_app


async def reconcile() -> dict[str, int]:
    if not activation_enabled():
        return {"disabled": 1}
    # Reuse the existing bounded Test Mode SDK client. No API checkout dependency
    # is invoked; the worker never consumes unsigned browser payment payloads.
    from app.api.checkout import _get_razorpay_client
    client = _get_razorpay_client()
    try:
        engine = create_database_engine(get_settings(), short_lived=True)
        try:
            return await scan_receipts(async_sessionmaker(engine, expire_on_commit=False), client)
        finally:
            await engine.dispose()
    finally:
        client.session.close()


@celery_app.task(name="app.tasks.payment_tasks.reconcile_payments", acks_late=True,
                 reject_on_worker_lost=True, soft_time_limit=630, time_limit=660)
def reconcile_payments() -> dict[str, int]:
    return asyncio.run(reconcile())
