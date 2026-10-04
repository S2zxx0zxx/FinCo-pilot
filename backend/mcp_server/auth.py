"""JWT verification for MCP requests.

The agent runtime (in the backend) mints a short-lived JWT per call,
signed with `AGENTS_MCP_JWT_SECRET`. We verify here. Same secret on both
sides; mismatched secret = 401 every time.
"""
from __future__ import annotations

import uuid
import time
from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException, Request, status
from jose import JWTError, jwt

from app.agents.config import get_agent_settings


JWT_ISSUER = "fincopilot-backend"
JWT_AUDIENCE = "fincopilot-mcp"
JWT_ALGO = "HS256"


@dataclass
class CallContext:
    user_id: uuid.UUID
    # External credentials always carry workspace scope. Explicitly purposed
    # internal calls may resolve the caller default workspace when omitted.
    workspace_id: Optional[uuid.UUID] = None
    conversation_id: Optional[uuid.UUID] = None
    agent_id: Optional[uuid.UUID] = None
    # True when the JWT was minted for an external agent (Claude Desktop,
    # n8n, etc.) rather than FinCo-Pilot's own runtime. External authorization
    # additionally requires a current registered workspace-scoped credential.
    external: bool = False
    token_id: Optional[uuid.UUID] = None


def _settings():
    return get_agent_settings()


def verify_request(request: Request) -> CallContext:
    auth = request.headers.get("authorization") or ""
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    token = auth.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(
            token, _settings().mcp_jwt_secret.get_secret_value(),
            algorithms=[JWT_ALGO], audience=JWT_AUDIENCE, issuer=JWT_ISSUER,
            options={"require_exp": True, "require_iat": True, "require_sub": True,
                     "require_aud": True, "require_iss": True},
        )
        if type(payload["exp"]) is not int or type(payload["iat"]) is not int:
            raise ValueError("Invalid dates")
        if payload["iat"] > time.time() + 60 or payload["exp"] <= payload["iat"]:
            raise ValueError("Invalid dates")
        purpose = payload.get("token_use")
        external = payload.get("ext", False)
        if type(external) is not bool:
            raise ValueError("Invalid purpose")
        # Old registered external tokens remain external. Tokens without an
        # explicit purpose/registry scope cannot masquerade as internal calls.
        if external:
            if purpose not in (None, "external") or not payload.get("ws_id") or not payload.get("jti"):
                raise ValueError("Unregistered legacy credential")
        elif purpose != "internal" or payload.get("jti"):
            raise ValueError("Ambiguous legacy credential")
        def identifier(name):
            value = payload.get(name)
            if value is None:
                return None
            if not isinstance(value, str):
                raise ValueError("Invalid identity")
            return uuid.UUID(value)
        user_id = identifier("sub")
        if user_id is None:
            raise ValueError("Missing identity")
        return CallContext(user_id=user_id, workspace_id=identifier("ws_id"),
                           conversation_id=identifier("conv_id"), agent_id=identifier("agent_id"),
                           external=external, token_id=identifier("jti"))
    except (JWTError, ValueError, TypeError, OverflowError, AttributeError, KeyError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid MCP credential; recreate legacy external tokens") from exc
