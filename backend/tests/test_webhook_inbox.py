"""Durable HTTP acceptance, unsigned-header safety and minimized encrypted evidence."""
import hashlib
import hmac
import asyncio
from contextlib import closing
import importlib.util
import json
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from pydantic import SecretStr
import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.api import payment_webhooks as ingress
from app.billing import webhook_inbox as inbox
from app.core.config import get_settings
from app.models.payment_webhook import PaymentWebhookEvent
from app.models.subscription import Subscription

SECRET = "synthetic-webhook-secret-0123456789"
KEY = "synthetic-financial-encryption-key-0123456789"
EVENT = {"entity": "event", "account_id": "acc_Synthetic", "event": "payment.captured",
         "created_at": 1, "payload": {"payment": {"entity": {
             "id": "pay_Synthetic", "entity": "payment", "order_id": "order_Synthetic",
             "amount": 1900, "currency": "INR", "status": "captured", "captured": True,
             "email": "private-canary@example.com", "contact": "9999999999",
             "card": {"number": "private-card-canary"}, "notes": {"private": "private-note-canary"}}}}}


@pytest.fixture
def enabled(monkeypatch):
    settings = get_settings()
    for key, value in {"razorpay_webhook_enabled": True, "razorpay_webhook_account_id": "acc_Synthetic",
                       "razorpay_webhook_secret": SecretStr(SECRET), "razorpay_webhook_mode": "test",
                       "credential_encryption_key": SecretStr(KEY)}.items():
        monkeypatch.setattr(settings, key, value)
    return settings


async def send(client, event=EVENT, hint="evt_Synthetic", invalid=False):
    body = json.dumps(event).encode()
    sig = hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
    headers = {"content-type": "application/json", "x-razorpay-signature": "0" * 64 if invalid else sig}
    if hint is not None:
        headers["x-razorpay-event-id"] = hint
    return await client.post("/api/webhooks/razorpay", content=body, headers=headers)


@pytest.mark.asyncio
async def test_committed_receipt_then_retry_and_header_substitution(client, session, clean_db, enabled):
    before = await session.scalar(select(func.count()).select_from(Subscription))
    for hint in ("evt_Synthetic", "evt_Tampered", None, "evt_Synthetic"):
        result = await send(client, hint=hint)
        assert result.status_code == 200 and result.json() == {"received": True}
        assert result.headers["cache-control"] == "no-store"
        assert "Synthetic" not in result.text
    rows = list((await session.scalars(select(PaymentWebhookEvent))).all())
    assert len(rows) == 1 and rows[0].state == "pending"
    row = rows[0]
    assert row.delivery_hint == "evt_Synthetic"
    snapshot = inbox.decrypt_snapshot(row)
    assert snapshot["payload"]["payment"]["entity"]["amount"] == 1900
    for canary in ("private-canary", "9999999999", "private-card-canary", "private-note-canary"):
        assert canary not in json.dumps(snapshot)
        assert canary not in row.snapshot_ciphertext
    assert "pay_Synthetic" not in row.snapshot_ciphertext
    assert await session.scalar(select(func.count()).select_from(Subscription)) == before


@pytest.mark.asyncio
async def test_same_unsigned_hint_cannot_poison_another_signed_body(client, session, clean_db, enabled):
    assert (await send(client)).status_code == 200
    other = json.loads(json.dumps(EVENT))
    other["payload"]["payment"]["entity"]["id"] = "pay_Another"
    assert (await send(client, other)).status_code == 200
    assert await session.scalar(select(func.count()).select_from(PaymentWebhookEvent)) == 2


@pytest.mark.asyncio
async def test_mode_isolation_and_unknown_quarantine(client, session, clean_db, enabled):
    assert (await send(client)).status_code == 200
    enabled.razorpay_webhook_mode = "live"
    assert (await send(client)).status_code == 200
    unknown = {**EVENT, "event": "unknown.received", "payload": {"notes": {"secret": "canary"}}}
    assert (await send(client, unknown)).status_code == 200
    rows = list((await session.scalars(select(PaymentWebhookEvent))).all())
    assert len(rows) == 3
    quarantined = next(row for row in rows if row.event_type == "unknown.received")
    assert quarantined.state == "quarantined" and inbox.decrypt_snapshot(quarantined)["payload"] == {}


@pytest.mark.asyncio
async def test_invalid_signature_never_persists(client, session, clean_db, enabled):
    assert (await send(client, invalid=True)).status_code == 401
    assert await session.scalar(select(func.count()).select_from(PaymentWebhookEvent)) == 0


@pytest.mark.asyncio
async def test_failed_commit_not_acknowledged_and_retry_is_safe(client, session, clean_db, enabled, monkeypatch):
    original = AsyncSession.commit

    async def failed(self):
        raise RuntimeError("private-db-canary")

    monkeypatch.setattr(AsyncSession, "commit", failed)
    result = await send(client)
    assert result.status_code == 503 and "canary" not in result.text
    assert await session.scalar(select(func.count()).select_from(PaymentWebhookEvent)) == 0
    monkeypatch.setattr(AsyncSession, "commit", original)
    assert (await send(client)).status_code == 200


@pytest.mark.asyncio
async def test_lost_commit_response_retry_finds_committed_receipt(client, session, clean_db, enabled, monkeypatch):
    original = AsyncSession.commit

    async def lost(self):
        await original(self)
        raise RuntimeError("Lost response")

    monkeypatch.setattr(AsyncSession, "commit", lost)
    assert (await send(client)).status_code == 503
    monkeypatch.setattr(AsyncSession, "commit", original)
    assert (await send(client)).status_code == 200
    assert await session.scalar(select(func.count()).select_from(PaymentWebhookEvent)) == 1


@pytest.mark.asyncio
async def test_rotation_binding_and_corruption_fail_closed(client, session, clean_db, enabled, monkeypatch):
    assert (await send(client)).status_code == 200
    row = await session.scalar(select(PaymentWebhookEvent))
    assert row is not None
    new_key = KEY + "-new"
    monkeypatch.setattr(inbox, "data_keys", lambda: (new_key, KEY))
    assert inbox.decrypt_snapshot(row)["event"] == "payment.captured"
    monkeypatch.setattr(inbox, "data_keys", lambda: (new_key,))
    with pytest.raises(ValueError):
        inbox.decrypt_snapshot(row)
    assert (await send(client)).status_code == 503
    monkeypatch.setattr(inbox, "data_keys", lambda: (KEY,))
    old_mode = row.mode
    row.mode = "live"
    with pytest.raises(ValueError):
        inbox.decrypt_snapshot(row)
    row.mode = old_mode
    row.snapshot_ciphertext = inbox.PREFIX + "invalid-token"
    await session.commit()
    assert (await send(client)).status_code == 503


def test_projection_only_accepts_financial_types():
    event = json.loads(json.dumps(EVENT))
    entity = event["payload"]["payment"]["entity"]
    entity.update(amount=True, currency="contact@example.com", status="private\ntext", order_id="email@example.com")
    snapshot, state = inbox.financial_snapshot(event)
    assert state == "pending"
    result = snapshot["payload"]["payment"]["entity"]
    assert not {"amount", "currency", "status", "order_id"} & result.keys()


@pytest.mark.asyncio
async def test_persistence_deadline_and_rollback_error_are_safe(client, session, clean_db, enabled, monkeypatch):
    async def slow(*args, **kwargs):
        await asyncio.sleep(1)

    async def bad_rollback(self):
        raise RuntimeError("private-rollback-canary")

    monkeypatch.setattr(ingress, "persist_webhook", slow)
    monkeypatch.setattr(ingress, "PERSIST_TIMEOUT_SECONDS", 0.01)
    monkeypatch.setattr(AsyncSession, "rollback", bad_rollback)
    result = await send(client)
    assert result.status_code == 503 and "canary" not in result.text


@pytest.mark.asyncio
async def test_first_body_without_header_is_durable(client, session, clean_db, enabled):
    assert (await send(client, hint=None)).status_code == 200
    assert (await send(client, hint="evt_NewHeader")).status_code == 200
    row = await session.scalar(select(PaymentWebhookEvent))
    assert row and row.delivery_hint is None
    assert await session.scalar(select(func.count()).select_from(PaymentWebhookEvent)) == 1


def test_malformed_entity_and_unknown_sensitive_payload_are_quarantined():
    event = json.loads(json.dumps(EVENT))
    event["payload"]["payment"]["entity"]["entity"] = "order"
    snapshot, state = inbox.financial_snapshot(event)
    assert state == "quarantined" and snapshot["payload"] == {}


def test_migration_upgrade_empty_rollback_and_evidence_refusal():
    path = Path(__file__).resolve().parents[1] / "alembic/versions/102_payment_webhook_events.py"
    spec = importlib.util.spec_from_file_location("webhook102", path)
    assert spec and spec.loader
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    # NullPool closes the DBAPI connection on context exit, including assertions.
    # A pooled in-memory engine otherwise leaks until nondeterministic GC on 3.14.
    from sqlalchemy.pool import NullPool

    engine = create_engine("sqlite://", poolclass=NullPool)
    with closing(engine.connect()) as connection, connection.begin():
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            migration.downgrade()
            migration.upgrade()
            connection.execute(text("INSERT INTO payment_webhook_events VALUES (:id,'razorpay','test','acc_Synthetic',:hash,'payment.captured',NULL,'pending','payment-inbox:v1:synthetic-ciphertext',CURRENT_TIMESTAMP)"),
                               {"id": "a" * 32, "hash": "b" * 64})
            with pytest.raises(RuntimeError, match="acknowledged"):
                migration.downgrade()
            assert connection.scalar(text("SELECT count(*) FROM payment_webhook_events")) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [("mode", "wrong"), ("provider", "other"),
                                         ("state", "fulfilled"), ("body_sha256", "short"),
                                         ("snapshot_ciphertext", "plaintext-private-canary")])
async def test_database_rejects_invalid_evidence_metadata(session, clean_db, field, value):
    fields = dict(provider="razorpay", mode="test", account_id="acc_Synthetic", body_sha256="a" * 64,
                  event_type="payment.captured", state="pending", snapshot_ciphertext=inbox.PREFIX + "synthetic")
    fields[field] = value
    session.add(PaymentWebhookEvent(**fields))
    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()
