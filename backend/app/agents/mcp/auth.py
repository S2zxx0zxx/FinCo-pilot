from __future__ import annotations

import time
import uuid
from typing import Optional

from jose import jwt

from app.agents.config import get_agent_settings


JWT_ISSUER = "fincopilot-backend"
JWT_AUDIENCE = "fincopilot-mcp"
JWT_ALGO = "HS256"


def mint_token(
    *,
    user_id: uuid.UUID,
    workspace_id: Optional[uuid.UUID] = None,
    conversation_id: Optional[uuid.UUID] = None,
    agent_id: Optional[uuid.UUID] = None,
    ttl_seconds: Optional[int] = None,
    external: bool = False,
    token_id: Optional[uuid.UUID] = None,
) -> str:
    """Mint explicitly purposed MCP credentials; external scope is mandatory."""
    if external and (workspace_id is None or token_id is None):
        raise ValueError("External credentials require workspace and registry identity")
    s = get_agent_settings()
    ttl = s.mcp_jwt_ttl_seconds if ttl_seconds is None else ttl_seconds
    if isinstance(ttl, bool) or not isinstance(ttl, int) or ttl <= 0:
        raise ValueError("Credential lifetime must be a positive integer")
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "iat": now,
        "exp": now + ttl,
        "token_use": "external" if external else "internal",
    }
    if workspace_id:
        payload["ws_id"] = str(workspace_id)
    if conversation_id:
        payload["conv_id"] = str(conversation_id)
    if agent_id:
        payload["agent_id"] = str(agent_id)
    if token_id:
        payload["jti"] = str(token_id)
    if external:
        payload["ext"] = True
    return jwt.encode(payload, s.mcp_jwt_secret.get_secret_value(), algorithm=JWT_ALGO)
