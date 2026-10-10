"""MCP server FastAPI app. JSON-RPC 2.0 over HTTP POST /mcp.

Exposes FinCo-Pilot's built-in tools (read-only + propose-mutations) over the
Model Context Protocol. Runs as a separate container; gated by the
`agents` profile in docker-compose.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from app.core.database import async_session_maker
from mcp_server import tools as _tools_pkg  # noqa: F401  triggers tool registration
from mcp_server.auth import verify_request
from mcp_server.registry import REGISTRY, call_tool, list_tools
from mcp_server.transport import (
    LEGACY_VERSIONS, MAX_BODY_BYTES, META_PREFIX, SUPPORTED_VERSIONS,
    valid_origin, validate_protocol,
)

logger = logging.getLogger(__name__)

app = FastAPI(title="FinCo-Pilot MCP Server", openapi_url=None, docs_url=None)


SERVER_INFO = {
    "name": "fincopilot-builtin",
    "version": "0.1.0",
}
PROTOCOL_VERSION = LEGACY_VERSIONS[0]


def _reject_constant(value):
    raise ValueError("Non-finite JSON is not supported")


@app.middleware("http")
async def transport_boundary(request: Request, call_next):
    if request.url.path == "/mcp":
        if not valid_origin(request):
            return JSONResponse(status_code=403, content=_err(None, -32600, "Origin not allowed"))
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response
    return await call_next(request)


def _err(req_id: Any, code: int, message: str, data: Any = None) -> dict:
    err: dict = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": req_id, "error": err}


def _ok(req_id: Any, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


@app.get("/health")
async def health():
    return {"status": "ok", "tools": len(REGISTRY)}


@app.post("/mcp")
async def mcp(request: Request) -> Response:
    # Auth first — never accept unauthenticated calls.
    try:
        ctx = verify_request(request)
    except Exception as exc:  # HTTPException from verify_request
        status_code = getattr(exc, "status_code", 401)
        detail = getattr(exc, "detail", str(exc))
        return JSONResponse(
            status_code=status_code,
            content={"jsonrpc": "2.0", "id": None, "error": {"code": -32001, "message": str(detail)}},
        )

    try:
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > MAX_BODY_BYTES:
                return JSONResponse(status_code=413, content=_err(None, -32600, "Request too large"))
        body = json.loads(raw, parse_constant=_reject_constant)
    except Exception:
        return JSONResponse(status_code=400, content=_err(None, -32700, "parse error"))

    if not isinstance(body, dict):
        return JSONResponse(status_code=400, content=_err(None, -32600, "invalid request"))

    req_id = body.get("id")
    method = body.get("method")
    params = body.get("params", {})

    if body.get("jsonrpc") != "2.0" or not isinstance(method, str):
        return JSONResponse(status_code=400, content=_err(req_id, -32600, "invalid request"))

    if not isinstance(params, dict):
        return JSONResponse(status_code=400, content=_err(req_id, -32602, "params must be an object"))
    if "id" in body and (type(req_id) not in (int, str)):
        return JSONResponse(status_code=400, content=_err(None, -32600, "invalid request id"))
    modern, protocol_error = validate_protocol(request, method, params)
    if protocol_error:
        code, message, data = protocol_error
        return JSONResponse(status_code=400, content=_err(req_id, code, message, data))

    def success(result: dict) -> JSONResponse:
        if modern:
            result = {**result, "resultType": "complete",
                      "_meta": {META_PREFIX + "serverInfo": SERVER_INFO}}
        return JSONResponse(content=_ok(req_id, result))

    if ctx.external and method != "tools/call":
        from mcp_server.registry import authorize_tool
        from fastapi import HTTPException
        try:
            async with async_session_maker() as session:
                await authorize_tool(session, ctx, None, {})
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content=_err(req_id, -32001, str(exc.detail)))
        except Exception:
            return JSONResponse(status_code=503, content=_err(req_id, -32001, "MCP authorization temporarily unavailable"))

    if "id" not in body:
        # Never execute a tools/call notification: financial actions need a
        # request/result and explicit app approval. Only lifecycle notices accepted.
        if not modern and method in ("notifications/initialized", "notifications/cancelled"):
            return Response(status_code=202)
        return JSONResponse(status_code=400, content=_err(None, -32600, "Unsupported notification"))

    if method == "server/discover" and modern:
        return success({"supportedVersions": list(SUPPORTED_VERSIONS), "capabilities": {"tools": {}}})

    if method == "ping":
        return success({})

    if method == "initialize" and not modern:
        requested = params.get("protocolVersion")
        version = requested if requested in LEGACY_VERSIONS else PROTOCOL_VERSION
        return success({
                "protocolVersion": version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": SERVER_INFO,
            })

    if method == "tools/list":
        if ctx.external:
            from mcp_server.registry import list_authorized_tools
            try:
                async with async_session_maker() as session:
                    tools = await list_authorized_tools(session, ctx)
            except Exception:
                logger.exception("MCP discovery unavailable")
                return JSONResponse(status_code=503, content=_err(req_id, -32603, "Tool discovery temporarily unavailable"))
        else:
            tools = list_tools()
        return success({"tools": tools})

    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(arguments, dict):
            return JSONResponse(status_code=400, content=_err(req_id, -32602, "arguments must be an object"))
        if not isinstance(name, str):
            return JSONResponse(content=_err(req_id, -32602, "tools/call requires 'name'"))
        try:
            async with async_session_maker() as session:
                result = await call_tool(session, ctx, name, arguments)
            # MCP wraps tool output in `content` blocks. Use the structured
            # variant — many clients (and our own runtime) prefer JSON.
            return success({
                "content": [{"type": "text", "text": _safe_json(result)}],
                "structuredContent": result,
                "isError": False,
            })
        except KeyError:
            return JSONResponse(content=_err(req_id, -32602 if modern else -32601, "Unknown tool"))
        except Exception:  # noqa: BLE001
            logger.exception("MCP tool failure: %s", name)
            return success({
                "content": [{"type": "text", "text": "Tool unavailable or access denied"}],
                "isError": True,
            })

    return JSONResponse(status_code=404 if modern else 200,
                        content=_err(req_id, -32601, "unknown method"))


def _safe_json(obj: Any) -> str:
    import json
    try:
        return json.dumps(obj, default=str)
    except Exception:
        return str(obj)
