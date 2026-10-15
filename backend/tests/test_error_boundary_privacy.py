"""Private upstream/SQL exceptions must not cross UI, task-result or log boundaries."""
import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from starlette.requests import Request

MARKER = "PRIVATE-SQL-parameters-and-provider-https://user:secret@example.invalid"


@pytest.mark.asyncio
async def test_custom_agent_unexpected_stream_error_is_generic(client, auth_headers, monkeypatch, caplog):
    from app.agents.runtime.executor import AgentExecutor

    async def fail(self, **kwargs):
        raise RuntimeError(MARKER)
        yield  # make the same asynchronous-generator interface as the executor

    monkeypatch.setattr(AgentExecutor, "run", fail)
    created = await client.post("/api/agents", headers=auth_headers, json={"name": "Privacy agent"})
    assert created.status_code == 201
    response = await client.post(f"/api/agents/{created.json()['id']}/chat", headers=auth_headers,
                                 json={"content": "hello"})
    assert response.status_code == 200
    assert "event: error" in response.text
    assert MARKER not in response.text
    assert MARKER not in caplog.text


def test_bank_worker_failure_result_is_generic(monkeypatch):
    from app.tasks import sync_tasks

    monkeypatch.setattr(sync_tasks, "_sync_one_celery", AsyncMock(side_effect=RuntimeError(MARKER)))
    result = sync_tasks.sync_single_connection.run("synthetic-connection", "synthetic-user")
    assert result["status"] == "error"
    assert result["connection_id"] == "synthetic-connection"
    assert MARKER not in result["error"]


@pytest.mark.parametrize("code", ["act.failed", MARKER])
def test_simplefin_warning_retains_only_known_code(code, caplog):
    from app.providers.simplefin import _surface_errors

    _surface_errors([{"code": code, "msg": MARKER, "account_id": MARKER}], "get_accounts")
    assert MARKER not in caplog.text
    if code == "act.failed":
        assert "act.failed" in caplog.text


@pytest.mark.asyncio
async def test_production_error_reference_omits_exception_and_token_path(monkeypatch, caplog):
    from app import main

    monkeypatch.setattr(main.settings, "deployment_environment", "production")
    request = Request({"type": "http", "method": "GET", "scheme": "https", "server": ("test", 443),
                       "path": "/synthetic/PRIVATE-token", "query_string": b"", "headers": [],
                       "route": SimpleNamespace(path="/synthetic/{token}")})

    async def fail(request):
        raise RuntimeError(MARKER)

    response = await main.request_reference(request, fail)
    assert response.status_code == 500
    assert response.headers["X-Request-ID"].startswith("FCREQ-")
    assert MARKER not in caplog.text
    assert "PRIVATE-token" not in caplog.text
    assert not any(record.exc_info for record in caplog.records)


def test_application_logs_do_not_emit_unredacted_tracebacks():
    """SQL and HTTP exceptions may contain parameters, tokens and private URLs."""
    violations = []
    backend = Path(__file__).parents[1]
    for path in [* (backend / "app").rglob("*.py"), * (backend / "mcp_server").rglob("*.py")]:
        for node in ast.walk(ast.parse(path.read_text())):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if not isinstance(node.func.value, ast.Name) or node.func.value.id != "logger":
                continue
            if node.func.attr == "exception" or any(
                kw.arg == "exc_info" and not (isinstance(kw.value, ast.Constant) and kw.value.value is False)
                for kw in node.keywords
            ):
                violations.append(f"{path.name}:{node.lineno}")
    assert not violations, violations


def test_container_entrypoints_disable_raw_url_access_logs():
    root = Path(__file__).parents[2]
    # Raw access targets include query reset tokens and capability URLs. Request
    # metrics and safe opaque-reference application diagnostics remain enabled.
    dockerfile = (root / "backend/Dockerfile").read_text()
    assert '"--no-access-log"' in dockerfile
    for name in ("docker-compose.yml", "docker-compose.prod.yml", "docker-compose.qa.yml"):
        text = (root / name).read_text()
        for line in text.splitlines():
            if "uvicorn " in line and not line.lstrip().startswith("#"):
                assert "--no-access-log" in line, (name, line)
    for component in ("backend", "mcp-server"):
        text = (root / f"charts/fincopilot/templates/{component}/deployment.yaml").read_text()
        assert "- --no-access-log" in text
