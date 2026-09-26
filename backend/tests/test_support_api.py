import pytest

from app.services.support_service import CreatedSupportTicket


@pytest.mark.asyncio
async def test_support_info_is_public_and_never_exposes_provider_secrets(client):
    response = await client.get("/api/support/info")
    assert response.status_code == 200
    assert response.headers["X-Request-ID"].startswith("FCREQ-")

    body = response.json()
    assert set(body) == {
        "enabled",
        "email",
        "portal_url",
        "help_center_url",
        "security_url",
        "direct_ticket_submission",
        "categories",
    }
    serialized = response.text.lower()
    assert "client_secret" not in serialized
    assert "refresh_token" not in serialized
    assert "org_id" not in serialized


@pytest.mark.asyncio
async def test_direct_support_submission_requires_authentication(client):
    response = await client.post(
        "/api/support/tickets",
        json={
            "category": "bug_performance",
            "subject": "A real support issue",
            "message": "The page fails after I open the dashboard.",
        },
    )
    assert response.status_code in {401, 403}


@pytest.mark.asyncio
async def test_direct_support_submission_uses_server_result(
    client, auth_headers, monkeypatch
):
    async def fake_create_support_ticket(**_kwargs):
        return CreatedSupportTicket(
            reference="FC-ABC123",
            ticket_id="provider-ticket-id",
            ticket_number="10042",
            support_tier="priority",
            priority="Medium",
        )

    monkeypatch.setattr(
        "app.api.support.create_support_ticket",
        fake_create_support_ticket,
    )

    response = await client.post(
        "/api/support/tickets",
        headers=auth_headers,
        json={
            "category": "bank_connection",
            "subject": "Bank sync stopped",
            "message": "My connection stopped refreshing after a successful sync.",
            "page_path": "/accounts",
            "app_version": "0.15.1",
            "locale": "en",
            "error_reference": "FCREQ-ABC123",
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "reference": "FC-ABC123",
        "ticket_id": "provider-ticket-id",
        "ticket_number": "10042",
        "support_tier": "priority",
        "priority": "Medium",
    }
