"""External protocol requests must never bypass credential/approval boundaries."""
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.agents.config import AgentSettings
from app.agents.mcp.auth import mint_token
from mcp_server.main import app
from mcp_server.transport import MODERN_VERSION, META_PREFIX, MAX_BODY_BYTES
from tests.conftest import TestSessionLocal


def modern(method, params=None):
    params = {**(params or {}), "_meta": {
        META_PREFIX + "protocolVersion": MODERN_VERSION,
        META_PREFIX + "clientCapabilities": {},
    }}
    headers = {"MCP-Protocol-Version": MODERN_VERSION, "Mcp-Method": method}
    if method == "tools/call":
        headers["Mcp-Name"] = params.get("name", "")
    return {"jsonrpc": "2.0", "id": 7, "method": method, "params": params}, headers


async def post(user, body, headers=None):
    auth = {"Authorization": "Bearer " + mint_token(user_id=user.id)}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://mcp.test") as cli:
        return await cli.post("/mcp", json=body, headers={**auth, **(headers or {})})


@pytest.mark.parametrize("version", ["2025-03-26", "2025-06-18", "2025-11-25"])
async def test_legacy_negotiates_and_accepts_initialized_notification(test_user, version):
    response = await post(test_user, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": version}})
    assert response.json()["result"]["protocolVersion"] == version
    response = await post(test_user, {"jsonrpc": "2.0", "method": "notifications/initialized"}, {"MCP-Protocol-Version": version})
    assert response.status_code == 202 and response.content == b""


async def test_modern_discovery_has_complete_result_and_supported_versions(test_user):
    body, headers = modern("server/discover")
    response = await post(test_user, body, headers)
    result = response.json()["result"]
    assert result["resultType"] == "complete"
    assert MODERN_VERSION in result["supportedVersions"]
    assert result["_meta"][META_PREFIX + "serverInfo"]["name"] == "fincopilot-builtin"
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("field", ["version", "method", "name", "capabilities"])
async def test_modern_header_or_metadata_mismatch_cannot_execute_tool(test_user, field):
    body, headers = modern("tools/call", {"name": "list_accounts", "arguments": {}})
    if field == "version":
        headers["MCP-Protocol-Version"] = "2025-11-25"
    elif field == "method":
        headers["Mcp-Method"] = "tools/list"
    elif field == "name":
        headers["Mcp-Name"] = "propose_create_transaction"
    else:
        del body["params"]["_meta"][META_PREFIX + "clientCapabilities"]
    with patch("mcp_server.main.call_tool", new=AsyncMock()) as tool:
        response = await post(test_user, body, headers)
        assert response.status_code == 400
        tool.assert_not_awaited()


async def test_unknown_modern_version_advertises_supported_without_execution(test_user):
    body, headers = modern("tools/list")
    headers["MCP-Protocol-Version"] = body["params"]["_meta"][META_PREFIX + "protocolVersion"] = "2099-01-01"
    response = await post(test_user, body, headers)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == -32022


@pytest.mark.parametrize("params", [[], None, 1, "bad"])
async def test_non_object_params_are_rejected(test_user, params):
    response = await post(test_user, {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": params})
    assert response.status_code == 400


@pytest.mark.parametrize("arguments", [[], None, 1, "bad"])
async def test_non_object_arguments_are_rejected(test_user, arguments):
    response = await post(test_user, {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "list_accounts", "arguments": arguments}})
    assert response.status_code == 400


async def test_tool_notification_is_rejected_without_execution(test_user):
    with patch("mcp_server.main.call_tool", new=AsyncMock()) as tool:
        response = await post(test_user, {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "propose_create_transaction", "arguments": {"apply": True}}})
        assert response.status_code == 400
        tool.assert_not_awaited()


@pytest.mark.parametrize("origin", ["null", "https://evil.example", "http://localhost:5173/path", "http://localhost:5173.evil"])
async def test_disallowed_browser_origin_is_rejected(test_user, origin):
    response = await post(test_user, {"jsonrpc": "2.0", "id": 1, "method": "ping"}, {"Origin": origin})
    assert response.status_code == 403


async def test_configured_origin_and_absent_origin_work(test_user):
    from app.core.config import get_settings
    from mcp_server.transport import origin_of
    for headers in ({}, {"Origin": origin_of(get_settings().frontend_url)}):
        assert (await post(test_user, {"jsonrpc": "2.0", "id": 1, "method": "ping"}, headers)).status_code == 200


async def test_oversized_request_rejected(test_user):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://mcp.test") as cli:
        response = await cli.post("/mcp", content=b"x" * (MAX_BODY_BYTES + 1), headers={"Authorization": "Bearer " + mint_token(user_id=test_user.id)})
    assert response.status_code == 413


async def test_revocation_denies_modern_discovery_and_notifications(client, auth_headers):
    minted = (await client.post("/api/agents/mcp-tokens", headers=auth_headers)).json()
    with patch("mcp_server.main.async_session_maker", TestSessionLocal), patch("app.billing.dependencies.require_workspace_capability", new=AsyncMock()):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://mcp.test") as cli:
            body, headers = modern("server/discover")
            headers["Authorization"] = "Bearer " + minted["token"]
            assert (await cli.post("/mcp", json=body, headers=headers)).status_code == 200
            assert (await client.delete("/api/agents/mcp-tokens/" + minted["id"], headers=auth_headers)).status_code == 204
            response = await cli.post("/mcp", json=body, headers=headers)
            assert response.status_code == 403
            response = await cli.post("/mcp", json={"jsonrpc": "2.0", "method": "notifications/initialized"}, headers={"Authorization": headers["Authorization"]})
            assert response.status_code == 403
            assert minted["token"] not in response.text


@pytest.mark.parametrize("url", ["https://user:secret@example.com/mcp", "https://example.com/mcp?token=secret", "https://example.com/mcp#secret", "javascript:bad", "https://example.com:bad/mcp"])
def test_endpoint_configuration_rejects_credential_or_invalid_urls(url):
    with pytest.raises(ValueError):
        AgentSettings(external_mcp_url=url, _env_file=None)


async def test_discovery_and_dispatch_share_module_and_safe_tool_boundaries(client, auth_headers, test_user, monkeypatch):
    from mcp_server.registry import REGISTRY, ToolSpec
    handler = AsyncMock(return_value={"unexpected": True})
    monkeypatch.setitem(REGISTRY, "hidden_business", ToolSpec("hidden_business", "hidden", {}, handler, tags=["read"], required_module="invoices"))
    monkeypatch.setitem(REGISTRY, "unsafe_write", ToolSpec("unsafe_write", "hidden", {}, handler, tags=["write"]))
    minted = (await client.post("/api/agents/mcp-tokens", headers=auth_headers)).json()
    with patch("mcp_server.main.async_session_maker", TestSessionLocal):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://mcp.test") as cli:
            body, headers = modern("tools/list")
            headers["Authorization"] = "Bearer " + minted["token"]
            response = await cli.post("/mcp", json=body, headers=headers)
            assert response.status_code == 200
            names = {tool["name"] for tool in response.json()["result"]["tools"]}
            assert "list_accounts" in names
            assert not {"hidden_business", "unsafe_write"} & names
            for name in ("hidden_business", "unsafe_write"):
                body, headers = modern("tools/call", {"name": name, "arguments": {}})
                headers["Authorization"] = "Bearer " + minted["token"]
                result = (await cli.post("/mcp", json=body, headers=headers)).json()["result"]
                assert result["isError"] is True
            handler.assert_not_awaited()


@pytest.mark.parametrize("header", ["=?base64?bGlzdF9hY2NvdW50cw==?=", "=?base64?invalid?="])
async def test_encoded_tool_name_is_validated_before_dispatch(test_user, header):
    body, headers = modern("tools/call", {"name": "list_accounts", "arguments": {}})
    headers["Mcp-Name"] = header
    with patch("mcp_server.main.call_tool", new=AsyncMock(return_value={"items": []})) as tool:
        response = await post(test_user, body, headers)
        if "invalid" in header:
            assert response.status_code == 400
            tool.assert_not_awaited()
        else:
            assert response.status_code == 200
            tool.assert_awaited_once()
