"""Razorpay authenticity boundary. Durable event acceptance belongs to #33."""

import asyncio
from dataclasses import dataclass, field
import hashlib
import hmac
import json
import math
import re
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.requests import ClientDisconnect

from app.core.config import get_settings

router = APIRouter(prefix="/api/webhooks", tags=["payment-webhooks"])
MAX_BODY_BYTES = 262_144
READ_TIMEOUT_SECONDS = 2


@dataclass(frozen=True)
class VerifiedWebhook:
    # Never include payment PII or signing material in a repr/log.
    body: bytes = field(repr=False)
    event: dict = field(repr=False)
    delivery_id: str | None = field(repr=False)


def _reject(status: int) -> HTTPException:
    return HTTPException(status, "Webhook unavailable" if status == 503 else "Invalid webhook",
                         headers={"Cache-Control": "no-store"})


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _nonfinite(value: str) -> None:
    raise ValueError("Nonfinite JSON number")


def _finite_float(value: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Nonfinite JSON number")
    return result


def _bounded_depth(value: object) -> None:
    stack = [(value, 0)]
    while stack:
        item, depth = stack.pop()
        if depth > 32:
            raise ValueError("Excessive JSON nesting")
        if isinstance(item, dict):
            stack.extend((child, depth + 1) for child in item.values())
        elif isinstance(item, list):
            stack.extend((child, depth + 1) for child in item)


async def verified_razorpay_webhook(request: Request) -> VerifiedWebhook:
    settings = get_settings()
    if not settings.razorpay_webhook_enabled:
        raise _reject(503)
    headers: dict[bytes, list[bytes]] = {}
    for key, value in request.scope["headers"]:
        headers.setdefault(key.lower(), []).append(value)
    for key in (b"x-razorpay-signature", b"content-length", b"content-type",
                b"content-encoding", b"x-razorpay-event-id"):
        if len(headers.get(key, [])) > 1:
            raise _reject(400)
    signature = headers.get(b"x-razorpay-signature", [b""])[0]
    if not re.fullmatch(rb"[0-9a-fA-F]{64}", signature):
        raise _reject(401)
    if headers.get(b"content-encoding", [b"identity"])[0].lower() != b"identity":
        raise _reject(415)
    if headers.get(b"content-type", [b""])[0].split(b";", 1)[0].strip().lower() != b"application/json":
        raise _reject(415)
    length = headers.get(b"content-length", [None])[0]
    if length is not None:
        if not re.fullmatch(rb"[0-9]{1,10}", length):
            raise _reject(400)
        if int(length) > MAX_BODY_BYTES:
            raise _reject(413)
    body = bytearray()
    try:
        async with asyncio.timeout(READ_TIMEOUT_SECONDS):
            async for chunk in request.stream():
                if len(body) + len(chunk) > MAX_BODY_BYTES:
                    raise _reject(413)
                body.extend(chunk)
    except TimeoutError:
        raise _reject(408) from None
    except ClientDisconnect:
        raise _reject(400) from None
    if length is not None and int(length) != len(body):
        raise _reject(400)
    raw = bytes(body)
    secrets = [settings.razorpay_webhook_secret.get_secret_value()]
    if (settings.razorpay_webhook_previous_secret.get_secret_value()
            and time.time() < settings.razorpay_webhook_previous_secret_expires_at):
        secrets.append(settings.razorpay_webhook_previous_secret.get_secret_value())
    valid = False
    for secret in secrets:
        digest = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest().encode()
        valid |= hmac.compare_digest(digest, signature.lower())
    if not valid:
        raise _reject(401)
    try:
        event = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs,
                           parse_constant=_nonfinite, parse_float=_finite_float)
        _bounded_depth(event)
        if (not isinstance(event, dict) or event.get("entity") != "event"
                or event.get("account_id") != settings.razorpay_webhook_account_id
                or not isinstance(event.get("event"), str)
                or len(event["event"]) > 128
                or not re.fullmatch(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+", event["event"])
                or not isinstance(event.get("payload"), dict)
                or type(event.get("created_at")) is not int or event["created_at"] < 0):
            raise ValueError("Invalid envelope")
    except (ValueError, RecursionError):
        raise _reject(400) from None
    delivery = headers.get(b"x-razorpay-event-id", [None])[0]
    if delivery is not None and not re.fullmatch(rb"[A-Za-z0-9_-]{1,128}", delivery):
        raise _reject(400)
    return VerifiedWebhook(raw, event, delivery.decode("ascii") if delivery else None)


@router.post("/razorpay", status_code=503)
async def razorpay_webhook(verified: VerifiedWebhook = Depends(verified_razorpay_webhook)):
    # A 2xx would discard a payment event before durable persistence exists.
    # No billing mutation, background task, or external API call is permitted here.
    raise _reject(503)
