"""Cold-start configuration rejection must remain safe and diagnosable."""

import json
import os
from pathlib import Path
import subprocess
import sys

from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel
import pytest

from app import vercel_entry


@pytest.fixture
async def blocked_client():
    async with AsyncClient(transport=ASGITransport(app=vercel_entry.configuration_blocked_app()), base_url="https://test.example") as client:
        yield client


@pytest.mark.parametrize("path", ["/api/health", "/api/health/live"])
async def test_liveness_does_not_claim_application_ready(blocked_client, path):
    response = await blocked_client.get(path)
    assert response.status_code == 200
    assert response.json() == {"status": "alive", "application_ready": False}
    assert response.headers["cache-control"] == "no-store"


async def test_readiness_is_sanitized_unavailable(blocked_client):
    response = await blocked_client.get("/api/health/ready?password=never-return-this")
    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {"configuration": {"ok": False, "error": "InvalidConfiguration"}},
    }
    assert "never-return-this" not in response.text
    assert response.headers["retry-after"] == "60"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-request-id"].startswith("FCREQ-")


@pytest.mark.parametrize("method,path", [
    ("GET", "/api/accounts"), ("POST", "/api/auth/login"),
    ("POST", "/api/setup"), ("POST", "/api/payment-webhooks/razorpay"),
    ("DELETE", "/api/users/me"), ("PATCH", "/api/loans/123"),
    ("GET", "/api/docs"), ("GET", "/api/openapi.json"),
    ("GET", "/metrics"), ("POST", "/mcp"), ("OPTIONS", "/api/accounts"),
    ("TRACE", "/anything"), ("CONNECT", "/anything"),
])
async def test_no_domain_docs_setup_or_provider_routes(blocked_client, method, path):
    response = await blocked_client.request(method, path, headers={
        "Origin": "https://attacker.example", "Authorization": "Bearer sensitive-token",
    }, content=b"sensitive-financial-payload")
    assert response.status_code == 503
    assert response.json()["code"] == "application_not_ready"
    assert "sensitive" not in response.text
    assert "access-control-allow-origin" not in response.headers
    assert response.headers["cache-control"] == "no-store"


async def test_websocket_is_never_accepted():
    messages = []

    async def receive():
        return {"type": "websocket.connect"}

    async def send(message):
        messages.append(message)

    await vercel_entry.configuration_blocked_app()({
        "type": "websocket", "path": "/api/agents/chat", "headers": [],
        "query_string": b"", "scheme": "wss", "root_path": "",
    }, receive, send)
    assert messages == [{"type": "websocket.close", "code": 1013, "reason": ""}]


def test_valid_configuration_returns_original_application():
    from app.main import app
    assert vercel_entry.create_app() is app


def test_configuration_failure_never_logs_validation_inputs(monkeypatch, caplog):
    class SecretBearingInput(BaseModel):
        value: int

    def invalid():
        SecretBearingInput.model_validate({"value": "postgresql://private:secret@host/db"})

    monkeypatch.setattr(vercel_entry, "get_settings", invalid)
    blocked = vercel_entry.create_app()
    assert blocked.openapi_url is None
    assert "blocked by invalid configuration" in caplog.text
    assert "private" not in caplog.text
    assert "secret@host" not in caplog.text


def test_unexpected_failure_is_not_disguised_as_configuration(monkeypatch):
    def broken():
        raise RuntimeError("unexpected internal failure")
    monkeypatch.setattr(vercel_entry, "get_settings", broken)
    with pytest.raises(RuntimeError, match="unexpected internal failure"):
        vercel_entry.create_app()


def test_real_invalid_production_cold_start_never_imports_domain_resources():
    # A fresh interpreter bypasses the suite's previously imported app/settings.
    # The sample values are synthetic; no production credentials are used.
    environment = dict(os.environ)
    environment.update({
        "DEPLOYMENT_ENVIRONMENT": "production", "EMAIL_DELIVERY_REQUIRED": "false",
        "LOCAL_AUTH_ENABLED": "true", "DATABASE_URL": "postgresql+asyncpg://private:synthetic-password@host/db",
    })
    result = subprocess.run([
        sys.executable, "-c",
        "import json,sys; from app.vercel_entry import app; "
        "print(json.dumps({'docs': app.openapi_url, 'domain': 'app.main' in sys.modules, "
        "'database': 'app.core.database' in sys.modules, 'auth': 'app.core.auth' in sys.modules}))",
    ], cwd=Path(__file__).parents[1], env=environment, capture_output=True, text=True,
        check=True, timeout=30)
    assert json.loads(result.stdout) == {"docs": None, "domain": False, "database": False, "auth": False}
    assert "synthetic-password" not in result.stderr
    assert "ValidationError" not in result.stderr
    assert "API bootstrap blocked by invalid configuration" in result.stderr
