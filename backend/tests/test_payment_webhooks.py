"""Synthetic provider ingress tests; never contact Razorpay or collect money."""
import hashlib
import hmac
import json
import time
from pathlib import Path
from typing import Any
import asyncio

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr, ValidationError
from starlette.requests import Request

from app.api import payment_webhooks as ingress
from app.core.config import Settings, get_settings
from app.main import app

SECRET = "synthetic-webhook-secret-0123456789"
OLD = "synthetic-previous-secret-0123456789"
BODY = json.dumps({"entity": "event", "account_id": "acc_Synthetic", "event": "payment.captured",
                   "payload": {"payment": {"entity": {"id": "pay_Synthetic"}}},
                   "created_at": 1}).encode()


def signature(body=BODY, secret=SECRET):
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.fixture
def enabled(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "razorpay_webhook_enabled", True)
    monkeypatch.setattr(settings, "razorpay_webhook_account_id", "acc_Synthetic")
    monkeypatch.setattr(settings, "razorpay_webhook_secret", SecretStr(SECRET))
    monkeypatch.setattr(settings, "razorpay_webhook_previous_secret", SecretStr(""))
    monkeypatch.setattr(settings, "razorpay_webhook_previous_secret_expires_at", 0)
    return settings


async def send(body=BODY, sig=None, headers=None):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.post("/api/webhooks/razorpay", content=body,
                                 headers=headers or {"content-type": "application/json",
                                                     "x-razorpay-signature": sig or signature(body)})


@pytest.mark.asyncio
async def test_valid_is_not_acknowledged_before_durable_handoff(enabled):
    response = await send()
    assert response.status_code == 503
    assert response.headers["cache-control"] == "no-store"
    assert "pay_Synthetic" not in response.text


@pytest.mark.asyncio
async def test_disabled_fails_closed(enabled):
    enabled.razorpay_webhook_enabled = False
    assert (await send()).status_code == 503


@pytest.mark.asyncio
async def test_raw_bytes_not_reserialized(enabled):
    assert (await send(BODY + b"\n", signature())).status_code == 401
    assert (await send(BODY + b"\n")).status_code == 503


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [b"{", b'"event"', b'{"entity":"event","entity":"event"}',
                                  b'{"value":NaN}', b"\xff", b"[" * 2000 + b"]" * 2000,
                                  BODY.replace(b"acc_Synthetic", b"acc_Other")])
async def test_signed_malformed_or_wrong_merchant_rejected(enabled, body):
    assert (await send(body)).status_code == 400


@pytest.mark.asyncio
@pytest.mark.parametrize("sig", ["x" * 64, "a" * 63, "a" * 65, "0" * 64])
async def test_invalid_signatures(enabled, sig):
    assert (await send(sig=sig)).status_code == 401


@pytest.mark.asyncio
async def test_rotation_and_expired_old_key(enabled):
    enabled.razorpay_webhook_previous_secret = SecretStr(OLD)
    enabled.razorpay_webhook_previous_secret_expires_at = int(time.time()) + 60
    assert (await send(sig=signature(secret=OLD))).status_code == 503
    enabled.razorpay_webhook_previous_secret_expires_at = int(time.time()) - 1
    assert (await send(sig=signature(secret=OLD))).status_code == 401
    assert (await send()).status_code == 503


@pytest.mark.asyncio
@pytest.mark.parametrize("extra,status", [([("content-encoding", "gzip")], 415),
                                         ([("x-razorpay-signature", signature())], 400),
                                         ([("x-razorpay-event-id", "bad id")], 400)])
async def test_security_headers(enabled, extra, status):
    headers = [("content-type", "application/json"), ("x-razorpay-signature", signature()), *extra]
    assert (await send(headers=headers)).status_code == status


@pytest.mark.asyncio
async def test_body_limits_even_without_content_length(enabled):
    sent = False

    async def receive():
        nonlocal sent
        assert not sent
        sent = True
        return {"type": "http.request", "body": b"x" * (ingress.MAX_BODY_BYTES + 1), "more_body": True}

    request = Request({"type": "http", "headers": [(b"content-type", b"application/json"),
                      (b"x-razorpay-signature", signature().encode())]}, receive)
    with pytest.raises(ingress.HTTPException) as error:
        await ingress.verified_razorpay_webhook(request)
    assert error.value.status_code == 413


@pytest.mark.parametrize("fields", [
    {"razorpay_webhook_secret": "short"},
    {"razorpay_webhook_secret": SECRET, "razorpay_key_secret": SECRET},
    {"razorpay_webhook_previous_secret": OLD},
    {"razorpay_webhook_enabled": True},
    {"razorpay_webhook_secret": " " + SECRET},
])
def test_bad_settings_fail_closed(fields):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **fields)


def test_configuration_and_production_secret_parity():
    root = Path(__file__).resolve().parents[2]
    for name in (".env.example", "docker-compose.yml", "docker-compose.prod.yml"):
        text = (root / name).read_text()
        for key in ("RAZORPAY_WEBHOOK_ENABLED", "RAZORPAY_WEBHOOK_ACCOUNT_ID",
                    "RAZORPAY_WEBHOOK_PREVIOUS_SECRET_EXPIRES_AT"):
            assert key in text
    production = (root / "docker-compose.prod.yml").read_text()
    for key in ("RAZORPAY_WEBHOOK_SECRET", "RAZORPAY_WEBHOOK_PREVIOUS_SECRET"):
        assert f"{key}:" not in production
    chart = (root / "charts/fincopilot/values.yaml").read_text()
    for key in ("razorpayWebhookEnabled", "razorpayWebhookAccountId", "razorpayWebhookSecret",
                "razorpayWebhookPreviousSecret", "razorpayWebhookPreviousSecretExpiresAt"):
        assert f"{key}:" in chart


def test_expiry_and_valid_config():
    fields: dict[str, Any] = {"razorpay_webhook_enabled": True, "razorpay_webhook_secret": SECRET,
              "razorpay_webhook_account_id": "acc_Synthetic",
              "razorpay_webhook_previous_secret": OLD,
              "razorpay_webhook_previous_secret_expires_at": int(time.time()) + 3600}
    assert Settings(_env_file=None, **fields).razorpay_webhook_enabled
    fields["razorpay_webhook_previous_secret_expires_at"] = int(time.time()) + 49 * 3600
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **fields)


def test_signature_equivalence_with_provider_sdk():
    from razorpay.utility.utility import Utility
    assert Utility().verify_webhook_signature(BODY.decode(), signature(), SECRET)


@pytest.mark.asyncio
async def test_slow_stream_deadline(enabled, monkeypatch):
    monkeypatch.setattr(ingress, "READ_TIMEOUT_SECONDS", 0.01)

    async def receive():
        await asyncio.sleep(1)
        return {"type": "http.request", "body": BODY}

    request = Request({"type": "http", "headers": [(b"content-type", b"application/json"),
                      (b"x-razorpay-signature", signature().encode())]}, receive)
    with pytest.raises(ingress.HTTPException) as error:
        await ingress.verified_razorpay_webhook(request)
    assert error.value.status_code == 408


@pytest.mark.asyncio
@pytest.mark.parametrize("length,status", [(b"-1", 400), (b"abc", 400),
                                          (b"262145", 413), (b"0", 400)])
async def test_declared_length_checks(enabled, length, status):
    async def receive():
        return {"type": "http.request", "body": BODY, "more_body": False}

    request = Request({"type": "http", "headers": [(b"content-type", b"application/json"),
                      (b"x-razorpay-signature", signature().encode()),
                      (b"content-length", length)]}, receive)
    with pytest.raises(ingress.HTTPException) as error:
        await ingress.verified_razorpay_webhook(request)
    assert error.value.status_code == status


@pytest.mark.asyncio
async def test_old_unicode_event_and_untrusted_delivery_header(enabled):
    body = BODY.replace(b'"pay_Synthetic"', '"हिन्दी"'.encode())
    headers = {"content-type": "application/json", "x-razorpay-signature": signature(body).upper(),
               "x-razorpay-event-id": "evt_Untrusted"}
    assert (await send(body, headers=headers)).status_code == 503
    assert "हिन्दी" not in repr(ingress.VerifiedWebhook(body, {}, "evt_Untrusted"))


@pytest.mark.asyncio
async def test_excessive_nesting_and_overflow_float(enabled):
    for value in [b"[" * 33 + b"0" + b"]" * 33, b"1e999"]:
        body = BODY.replace(b'"pay_Synthetic"', value)
        assert (await send(body)).status_code == 400


@pytest.mark.asyncio
async def test_finite_payload_number_is_accepted_without_activation(enabled):
    assert (await send(BODY.replace(b'"pay_Synthetic"', b"1.25"))).status_code == 503


@pytest.mark.asyncio
async def test_non_json_media_rejected(enabled):
    headers = {"content-type": "text/plain", "x-razorpay-signature": signature()}
    assert (await send(headers=headers)).status_code == 415


@pytest.mark.asyncio
async def test_disconnected_stream_has_safe_failure(enabled):
    async def receive():
        return {"type": "http.disconnect"}

    request = Request({"type": "http", "headers": [(b"content-type", b"application/json"),
                      (b"x-razorpay-signature", signature().encode())]}, receive)
    with pytest.raises(ingress.HTTPException) as error:
        await ingress.verified_razorpay_webhook(request)
    assert error.value.status_code == 400
    assert error.value.headers == {"Cache-Control": "no-store"}
