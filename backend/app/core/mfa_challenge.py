"""One-use login challenges shared by TOTP, recovery codes and passkeys."""
import json
import secrets

from fastapi import HTTPException
from redis.asyncio import Redis

from app.core.auth import get_jwt_strategy
from app.models.user import User


async def consume_login_challenge(redis: Redis, temp_token: str, user: User, method: str) -> None:
    # GETDEL is atomic across workers and factor methods. Validate after consuming:
    # no bearer token may be issued from a stale pre-verification GET result.
    try:
        raw = await redis.getdel(f"2fa_temp:{temp_token}")
    except Exception:
        raise HTTPException(503, "Authentication service unavailable") from None
    try:
        payload = json.loads(raw) if isinstance(raw, (str, bytes)) else None
    except (ValueError, TypeError):
        payload = None
    methods = payload.get("available_methods") if isinstance(payload, dict) else None
    stamp = payload.get("credential_stamp") if isinstance(payload, dict) else None
    if (not isinstance(payload, dict) or not isinstance(methods, list) or method not in methods
            or payload.get("user_id") != str(user.id) or not user.is_active
            or not user.is_2fa_enabled or not user.totp_secret
            or not isinstance(stamp, str) or not secrets.compare_digest(stamp, get_jwt_strategy().stamp(user))):
        raise HTTPException(401, "Invalid or expired login challenge")
