"""Vercel bootstrap: invalid settings expose health only, never domain routes.

Container/worker entrypoints retain their existing strict startup behavior.
Unexpected import failures are deliberately not converted to configuration errors.
"""

import logging
import secrets

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def configuration_blocked_app() -> FastAPI:
    blocked = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)

    @blocked.middleware("http")
    async def response_policy(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Request-ID"] = "FCREQ-" + secrets.token_hex(6).upper()
        if response.status_code == 503:
            response.headers["Retry-After"] = "60"
        return response

    @blocked.api_route("/api/health", methods=["GET", "HEAD"])
    @blocked.api_route("/api/health/live", methods=["GET", "HEAD"])
    async def liveness():
        # This proves only that the diagnostic process can answer requests.
        return {"status": "alive", "application_ready": False}

    @blocked.api_route("/api/health/ready", methods=["GET", "HEAD"])
    async def readiness():
        return JSONResponse(status_code=503, content={
            "status": "not_ready",
            "checks": {"configuration": {"ok": False, "error": "InvalidConfiguration"}},
        })

    @blocked.api_route("/{path:path}", methods=[
        "GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE", "CONNECT",
    ])
    async def unavailable(path: str):
        return JSONResponse(status_code=503, content={
            "detail": "The application is temporarily unavailable.",
            "code": "application_not_ready",
        })

    @blocked.websocket("/{path:path}")
    async def unavailable_websocket(websocket: WebSocket, path: str):
        await websocket.close(code=1013)

    return blocked


def create_app() -> FastAPI:
    try:
        get_settings()
    except ValidationError:
        # Pydantic errors/context can contain URLs, credentials or input values.
        # Do not log the exception, validation details, environment or request.
        logger.error("API bootstrap blocked by invalid configuration")
        return configuration_blocked_app()

    # Validate before importing modules that initialize DB/auth/provider clients.
    from app.main import app

    return app


app = create_app()
