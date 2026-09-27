import json
import logging
import uuid
from types import SimpleNamespace
from typing import cast
from urllib.parse import parse_qs

import httpx
import pytest
from fastapi import HTTPException
from pydantic import SecretStr, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.enums import PlanId
from app.models.user import User
from app.schemas.support import SupportCategory, SupportTicketCreate
from app.services import support_service


def _zoho_settings():
    return SimpleNamespace(
        zoho_desk_accounts_domain="https://accounts.zoho.in",
        zoho_desk_api_domain="https://desk.zoho.in",
        zoho_desk_org_id="org-123",
        zoho_desk_department_id="department-456",
        zoho_desk_client_id="client-789",
        zoho_desk_client_secret=SecretStr("client-secret-value"),
        zoho_desk_refresh_token=SecretStr("refresh-token-value"),
    )


def _install_mock_transport(monkeypatch, handler):
    real_async_client = httpx.AsyncClient
    transport = httpx.MockTransport(handler)

    def factory(*args, **kwargs):
        kwargs["transport"] = transport
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(support_service.httpx, "AsyncClient", factory)


@pytest.mark.asyncio
async def test_zoho_ticket_contract_uses_refresh_oauth_and_escaped_html(monkeypatch):
    settings = _zoho_settings()
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "accounts.zoho.in":
            assert request.url.path == "/oauth/v2/token"
            form = parse_qs(request.content.decode())
            assert form == {
                "refresh_token": ["refresh-token-value"],
                "client_id": ["client-789"],
                "client_secret": ["client-secret-value"],
                "grant_type": ["refresh_token"],
            }
            return httpx.Response(
                200,
                json={
                    "access_token": "access-token-value",
                    "api_domain": "https://desk.zoho.in",
                },
            )

        assert request.url == httpx.URL("https://desk.zoho.in/api/v1/tickets")
        seen["authorization"] = request.headers["Authorization"]
        seen["org_id"] = request.headers["orgId"]
        seen["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"id": "provider-id-1", "ticketNumber": "10042"})

    monkeypatch.setattr(support_service, "get_settings", lambda: settings)
    _install_mock_transport(monkeypatch, handler)

    provider = support_service.ZohoDeskClient()
    ticket_id, ticket_number = await provider.create_ticket(
        requester_email="person@example.test",
        subject="[FC-ABC123] Login issue",
        description="<script>alert('x')</script>\nSecond line",
        priority="High",
    )

    assert ticket_id == "provider-id-1"
    assert ticket_number == "10042"
    assert seen["authorization"] == "Zoho-oauthtoken access-token-value"
    assert seen["org_id"] == "org-123"
    assert seen["payload"] == {
        "departmentId": "department-456",
        "subject": "[FC-ABC123] Login issue",
        "description": "&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt;<br>Second line",
        "email": "person@example.test",
        "channel": "Web",
        "priority": "High",
        "status": "Open",
    }


@pytest.mark.asyncio
async def test_zoho_provider_failure_does_not_log_response_body(monkeypatch, caplog):
    settings = _zoho_settings()
    provider_echo = "DO-NOT-LOG-provider-echo-sensitive"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "accounts.zoho.in":
            return httpx.Response(
                200,
                json={
                    "access_token": "access-token-value",
                    "api_domain": "https://desk.zoho.in",
                },
            )
        return httpx.Response(500, text=provider_echo)

    monkeypatch.setattr(support_service, "get_settings", lambda: settings)
    _install_mock_transport(monkeypatch, handler)
    caplog.set_level(logging.ERROR)

    with pytest.raises(
        support_service.SupportDeliveryError,
        match="did not confirm ticket creation",
    ):
        await support_service.ZohoDeskClient().create_ticket(
            requester_email="person@example.test",
            subject="Support issue",
            description="Safe description",
            priority="Medium",
        )

    assert provider_echo not in caplog.text
    assert "access-token-value" not in caplog.text
    assert "refresh-token-value" not in caplog.text


@pytest.mark.asyncio
async def test_zoho_missing_provider_ticket_id_fails_closed(monkeypatch):
    settings = _zoho_settings()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "accounts.zoho.in":
            return httpx.Response(
                200,
                json={
                    "access_token": "access-token-value",
                    "api_domain": "https://desk.zoho.in",
                },
            )
        return httpx.Response(200, json={"ticketNumber": "10042"})

    monkeypatch.setattr(support_service, "get_settings", lambda: settings)
    _install_mock_transport(monkeypatch, handler)

    with pytest.raises(
        support_service.SupportDeliveryError,
        match="returned no ticket id",
    ):
        await support_service.ZohoDeskClient().create_ticket(
            requester_email="person@example.test",
            subject="Support issue",
            description="Safe description",
            priority="Low",
        )


@pytest.mark.asyncio
async def test_create_support_ticket_uses_server_plan_and_safe_diagnostics(monkeypatch):
    user_id = uuid.uuid4()
    user = cast(User, SimpleNamespace(id=user_id, email="person@example.test"))
    observed: dict[str, object] = {}

    async def no_rate_limit(_user_id):
        assert _user_id == user_id

    async def effective_plan(_session, _user_id):
        assert _user_id == user_id
        return PlanId.PRO

    class Provider:
        async def create_ticket(self, **kwargs):
            observed.update(kwargs)
            return "provider-id-1", "10042"

    monkeypatch.setattr(
        support_service,
        "get_settings",
        lambda: SimpleNamespace(support_ticket_submission_available=True),
    )
    monkeypatch.setattr(support_service, "enforce_support_rate_limit", no_rate_limit)
    monkeypatch.setattr(support_service, "get_effective_plan", effective_plan)
    monkeypatch.setattr(support_service, "make_support_reference", lambda: "FC-ABC123")
    monkeypatch.setattr(support_service, "ZohoDeskClient", Provider)

    ticket = SupportTicketCreate(
        category=SupportCategory.BANK_CONNECTION,
        subject="Bank refresh stopped",
        message="The bank refresh stopped after a successful connection.",
        page_path="/accounts?oauth_code=must-not-survive",
        app_version="0.15.1",
        locale="en",
        error_reference="FCREQ-A1B2C3D4E5F6",
    )
    result = await support_service.create_support_ticket(
        session=cast(AsyncSession, object()),
        user=user,
        ticket=ticket,
        request_reference="FCREQ-111122223333",
        user_agent="FinCo-Test/1.0",
    )

    assert result.reference == "FC-ABC123"
    assert result.ticket_id == "provider-id-1"
    assert result.ticket_number == "10042"
    assert result.support_tier == "priority"
    assert result.priority == "Medium"
    assert observed["requester_email"] == "person@example.test"
    assert observed["subject"] == "[FC-ABC123] Bank refresh stopped"
    assert observed["priority"] == "Medium"
    description = str(observed["description"])
    assert "Page: /accounts" in description
    assert "oauth_code" not in description
    assert "Plan: pro" in description
    assert "Support tier: priority" in description
    assert "Previous error reference: FCREQ-A1B2C3D4E5F6" in description


@pytest.mark.asyncio
async def test_sensitive_diagnostics_are_rejected_before_rate_limit(monkeypatch):
    user = cast(User, SimpleNamespace(id=uuid.uuid4(), email="person@example.test"))
    reached_rate_limit = False

    async def should_not_run(_user_id):
        nonlocal reached_rate_limit
        reached_rate_limit = True

    monkeypatch.setattr(
        support_service,
        "get_settings",
        lambda: SimpleNamespace(support_ticket_submission_available=True),
    )
    monkeypatch.setattr(support_service, "enforce_support_rate_limit", should_not_run)

    ticket = SupportTicketCreate(
        category=SupportCategory.BUG_PERFORMANCE,
        subject="Browser issue",
        message="The page fails after the dashboard loads.",
    )

    with pytest.raises(HTTPException) as exc:
        await support_service.create_support_ticket(
            session=object(),
            user=user,
            ticket=ticket,
            request_reference="FCREQ-111122223333",
            user_agent="FinCo-Test bearer abcdefghijklmnopqrstuvwxyz",
        )

    assert exc.value.status_code == 422
    assert reached_rate_limit is False


@pytest.mark.asyncio
async def test_provider_failure_maps_to_single_safe_502_without_retry(monkeypatch):
    user = SimpleNamespace(id=uuid.uuid4(), email="person@example.test")
    calls = 0

    async def no_rate_limit(_user_id):
        return None

    async def effective_plan(_session, _user_id):
        return PlanId.MAX

    class Provider:
        async def create_ticket(self, **_kwargs):
            nonlocal calls
            calls += 1
            raise support_service.SupportDeliveryError("provider detail that must stay internal")

    monkeypatch.setattr(
        support_service,
        "get_settings",
        lambda: SimpleNamespace(support_ticket_submission_available=True),
    )
    monkeypatch.setattr(support_service, "enforce_support_rate_limit", no_rate_limit)
    monkeypatch.setattr(support_service, "get_effective_plan", effective_plan)
    monkeypatch.setattr(support_service, "make_support_reference", lambda: "FC-FAIL12345")
    monkeypatch.setattr(support_service, "ZohoDeskClient", Provider)

    ticket = SupportTicketCreate(
        category=SupportCategory.PRIVACY_DATA,
        subject="Privacy request",
        message="Please help me with my account privacy request.",
    )

    with pytest.raises(HTTPException) as exc:
        await support_service.create_support_ticket(
            session=object(),
            user=user,
            ticket=ticket,
            request_reference="FCREQ-111122223333",
            user_agent="FinCo-Test/1.0",
        )

    assert calls == 1
    assert exc.value.status_code == 502
    assert exc.value.detail == {
        "code": "SUPPORT_PROVIDER_UNAVAILABLE",
        "message": (
            "The support provider did not confirm ticket creation. "
            "No automatic retry was attempted to avoid duplicate tickets."
        ),
        "reference": "FC-FAIL12345",
    }
    assert "provider detail" not in str(exc.value.detail)


def test_support_diagnostic_schema_rejects_host_paths_and_fake_references():
    with pytest.raises(ValidationError):
        SupportTicketCreate(
            category=SupportCategory.OTHER,
            subject="Need help",
            message="This is a valid support message.",
            page_path="//evil.example/path",
        )

    with pytest.raises(ValidationError):
        SupportTicketCreate(
            category=SupportCategory.OTHER,
            subject="Need help",
            message="This is a valid support message.",
            error_reference="Bearer secret-that-must-not-pass",
        )

    normalized = SupportTicketCreate(
        category=SupportCategory.OTHER,
        subject="Need help",
        message="This is a valid support message.",
        error_reference="fcreq-a1b2c3d4e5f6",
    )
    assert normalized.error_reference == "FCREQ-A1B2C3D4E5F6"
