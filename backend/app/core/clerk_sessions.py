"""Clerk JWT verification foundation. Intentionally NOT wired into app routes.

This verifies cryptographic identity, not permission to access a financial resource.
A separate DB identity lookup and existing workspace/billing guards are required.
"""
from dataclasses import dataclass

import jwt


class ClerkTokenError(ValueError):
    """Reject an untrusted, expired, or unsupported Clerk session token."""


@dataclass(frozen=True)
class VerifiedClerkSession:
    user_id: str
    session_id: str
    issuer: str


def verify_clerk_session(
    token: str,
    *,
    issuer: str,
    public_key_pem: str,
    authorized_parties: tuple[str, ...],
    audience: str | None = None,
) -> VerifiedClerkSession:
    """Fail-closed local RS256 verification of a Clerk session JWT.

    The caller must supply the exact HTTPS issuer and explicit allowed origins.
    Missing azp is rejected by this financial app even though Clerk may omit it
    for some no-Origin clients; supported clients must send an authorized origin.
    Session checks do not replace real-time revoked-session/lockout checks.
    """
    if (
        not issuer.startswith("https://")
        or not public_key_pem.strip()
        or not authorized_parties
        or any(not party.startswith(("https://", "http://localhost:")) for party in authorized_parties)
    ):
        raise ClerkTokenError("Clerk verification configuration is incomplete")
    if not isinstance(token, str) or not token.strip():
        raise ClerkTokenError("Missing Clerk session token")

    try:
        claims = jwt.decode(
            token,
            public_key_pem,
            algorithms=["RS256"],
            issuer=issuer,
            audience=audience,
            leeway=5,
            options={
                "require": ["iss", "sub", "sid", "iat", "nbf", "exp", "azp"],
                "verify_aud": audience is not None,
            },
        )
    except (jwt.PyJWTError, ValueError, TypeError) as exc:
        raise ClerkTokenError("Invalid Clerk session token") from exc

    user_id = claims.get("sub")
    session_id = claims.get("sid")
    if not isinstance(user_id, str) or not user_id.startswith("user_"):
        raise ClerkTokenError("Invalid Clerk user subject")
    if not isinstance(session_id, str) or not session_id.startswith("sess_"):
        raise ClerkTokenError("Invalid Clerk session")
    if claims.get("azp") not in authorized_parties:
        raise ClerkTokenError("Unauthorized Clerk token origin")
    if "sts" in claims and claims["sts"] != "active":
        raise ClerkTokenError("Clerk session is not active")
    if "act" in claims:
        raise ClerkTokenError("Impersonation is not permitted for financial access")
    return VerifiedClerkSession(user_id=user_id, session_id=session_id, issuer=issuer)
