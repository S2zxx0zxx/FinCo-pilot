"""Pure lifecycle classification; never expose or persist bearer token values."""
import hmac
import re
from datetime import datetime, timezone

from app.models.mcp_token import ExternalMCPToken


def external_token_status(row: ExternalMCPToken, current_stamp: str, now: datetime) -> str:
    if row.revoked:
        return "revoked"
    expiry = row.expires_at.replace(tzinfo=timezone.utc) if row.expires_at.tzinfo is None else row.expires_at
    if expiry <= now:
        return "expired"
    stamp = row.credential_stamp
    if not isinstance(stamp, str) or re.fullmatch(r"[0-9a-f]{64}", stamp) is None or not hmac.compare_digest(stamp, current_stamp):
        return "credential_changed"
    return "active"
