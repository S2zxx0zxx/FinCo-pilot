"""Commit-before-ack transport receipts, without subscription fulfillment."""
import base64
from datetime import datetime, timezone
import functools
import hashlib
import json
import re
import uuid

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.credential_keys import data_keys
from app.models.payment_webhook import PaymentWebhookEvent

PREFIX = "payment-inbox:v1:"
ENTITY_PREFIXES = {"payment": "pay", "order": "order", "refund": "rfnd",
                   "subscription": "sub", "invoice": "inv", "payment.downtime": "down"}
ID_FIELDS = {"order_id": "order", "payment_id": "pay", "subscription_id": "sub",
             "invoice_id": "inv", "plan_id": "plan"}
INTEGER_FIELDS = {"amount", "amount_paid", "amount_due", "amount_refunded", "total_count",
                  "paid_count", "remaining_count", "current_start", "current_end", "charge_at",
                  "created_at", "start_at", "end_at"}


def _identifier(value: object, prefix: str) -> bool:
    return isinstance(value, str) and re.fullmatch(prefix + r"_[A-Za-z0-9]{1,100}", value) is not None


def financial_snapshot(event: dict) -> tuple[dict, str]:
    """Discard arbitrary nested data and PII; never retain the raw body."""
    payload = {}
    for name, prefix in ENTITY_PREFIXES.items():
        wrapper = event["payload"].get(name)
        entity = wrapper.get("entity") if isinstance(wrapper, dict) else None
        if (not isinstance(entity, dict) or entity.get("entity") != name
                or not _identifier(entity.get("id"), prefix)):
            continue
        clean = {"id": entity["id"], "entity": name}
        for key, id_prefix in ID_FIELDS.items():
            if _identifier(entity.get(key), id_prefix):
                clean[key] = entity[key]
        for key in INTEGER_FIELDS:
            value = entity.get(key)
            if type(value) is int and 0 <= value <= 2**63 - 1:
                clean[key] = value
        if type(entity.get("captured")) is bool:
            clean["captured"] = entity["captured"]
        status = entity.get("status")
        if isinstance(status, str) and re.fullmatch(r"[a-z][a-z_]{0,31}", status):
            clean["status"] = status
        currency = entity.get("currency")
        if isinstance(currency, str) and re.fullmatch(r"[A-Z]{3}", currency):
            clean["currency"] = currency
        payload[name] = {"entity": clean}
    snapshot = {key: event[key] for key in ("entity", "account_id", "event", "created_at")}
    snapshot["payload"] = payload
    state = "pending" if any(event["event"].startswith(name + ".") for name in payload) else "quarantined"
    return snapshot, state


@functools.lru_cache(maxsize=32)
def _cipher(key: str) -> Fernet:
    derived = HKDF(algorithm=hashes.SHA256(), length=32, salt=b"fincopilot-payment-inbox-v1",
                   info=b"financial-snapshot-encryption").derive(key.encode())
    return Fernet(base64.urlsafe_b64encode(derived))


def encrypt_snapshot(snapshot: dict, *, mode: str, body_sha256: str) -> str:
    envelope = {"mode": mode, "body_sha256": body_sha256, "snapshot": snapshot}
    raw = json.dumps(envelope, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode()
    return PREFIX + _cipher(data_keys()[0]).encrypt(raw).decode("ascii")


def decrypt_snapshot(row: PaymentWebhookEvent) -> dict:
    if not row.snapshot_ciphertext.startswith(PREFIX):
        raise ValueError("Payment snapshot unavailable")
    for key in data_keys():
        try:
            raw = _cipher(key).decrypt(row.snapshot_ciphertext[len(PREFIX):].encode())
            envelope = json.loads(raw)
            snapshot = envelope["snapshot"]
            if (envelope["mode"] != row.mode or envelope["body_sha256"] != row.body_sha256
                    or snapshot["account_id"] != row.account_id or snapshot["event"] != row.event_type):
                raise ValueError("Snapshot binding mismatch")
            return snapshot
        except (InvalidToken, ValueError, KeyError, TypeError, UnicodeError):
            continue
    raise ValueError("Payment snapshot unavailable")


async def persist_webhook(session: AsyncSession, *, body: bytes, event: dict,
                          delivery_id: str | None, mode: str) -> None:
    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        await session.execute(text("SET LOCAL statement_timeout = '1500ms'"))
        await session.execute(text("SET LOCAL lock_timeout = '1000ms'"))
        insert = pg_insert
    elif dialect == "sqlite":
        insert = sqlite_insert
    else:
        raise ValueError("Unsupported webhook database")
    body_hash = hashlib.sha256(body).hexdigest()
    snapshot, state = financial_snapshot(event)
    ciphertext = encrypt_snapshot(snapshot, mode=mode, body_sha256=body_hash)
    row_id = uuid.uuid4()
    result = await session.execute(insert(PaymentWebhookEvent).values(
        id=row_id, provider="razorpay", mode=mode, account_id=event["account_id"],
        body_sha256=body_hash, event_type=event["event"], delivery_hint=delivery_id,
        state=state, snapshot_ciphertext=ciphertext, received_at=datetime.now(timezone.utc),
    ).on_conflict_do_nothing(index_elements=["provider", "mode", "account_id", "body_sha256"])
      .returning(PaymentWebhookEvent.id))
    if result.scalar_one_or_none() is None:
        # A separate READ COMMITTED statement sees a concurrent winner after its
        # unique-index conflict resolves. Only confirm an intact durable receipt.
        existing = await session.scalar(select(PaymentWebhookEvent).where(
            PaymentWebhookEvent.provider == "razorpay", PaymentWebhookEvent.mode == mode,
            PaymentWebhookEvent.account_id == event["account_id"], PaymentWebhookEvent.body_sha256 == body_hash))
        if existing is None:
            raise ValueError("Existing receipt unavailable")
        stored = decrypt_snapshot(existing)
        # Preserve the first committed projection. A future allowlist expansion
        # must not invalidate a legitimate old receipt with the same signed bytes.
        if any(stored.get(key) != event[key] for key in ("entity", "account_id", "event", "created_at")):
            raise ValueError("Existing receipt unavailable")
    # A failed/lost commit result is not acknowledged; retries find the same row.
    await session.commit()
