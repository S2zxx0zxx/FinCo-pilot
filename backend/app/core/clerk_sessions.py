"""Clerk JWT verification used by the explicit external identity exchange.

This verifies cryptographic identity, not permission to access a financial resource.
A separate DB identity lookup and existing workspace/billing guards are required.
"""
import time
import re
from dataclasses import dataclass

import httpx
import jwt
from cryptography.hazmat.primitives import serialization

from app.core.config import get_settings


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
    if not isinstance(user_id, str) or not re.fullmatch(r"user_[A-Za-z0-9_]+", user_id):
        raise ClerkTokenError("Invalid Clerk user subject")
    if not isinstance(session_id, str) or not re.fullmatch(r"sess_[A-Za-z0-9_]+", session_id):
        raise ClerkTokenError("Invalid Clerk session")
    if claims.get("azp") not in authorized_parties:
        raise ClerkTokenError("Unauthorized Clerk token origin")
    if "sts" in claims and claims["sts"] != "active":
        raise ClerkTokenError("Clerk session is not active")
    if "act" in claims:
        raise ClerkTokenError("Impersonation is not permitted for financial access")
    return VerifiedClerkSession(user_id=user_id, session_id=session_id, issuer=issuer)


_JWKS_CACHE: dict[str, tuple[float, str]] = {}
JWKS_CACHE_TTL = 3600  # 1 hour


async def get_or_fetch_clerk_public_key(issuer: str, key_id: str | None = None) -> str:
    """Return configured PEM public key or fetch and cache from Clerk JWKS."""
    settings = get_settings()
    configured_pem = settings.clerk_jwt_public_key.strip()
    if configured_pem:
        return configured_pem

    cache_key = f"{issuer}:{key_id or 'default'}"
    cached = _JWKS_CACHE.get(cache_key)
    now = time.time()
    if cached and (now - cached[0]) < JWKS_CACHE_TTL:
        return cached[1]

    jwks_url = f"{issuer.rstrip('/')}/.well-known/jwks.json"
    jwks = None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(jwks_url)
            if resp.status_code == 200:
                jwks = resp.json()
    except Exception:
        pass

    if not jwks and settings.clerk_secret_key.get_secret_value().strip():
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://api.clerk.com/v1/jwks",
                    headers={"Authorization": f"Bearer {settings.clerk_secret_key.get_secret_value().strip()}"},
                )
                if resp.status_code == 200:
                    jwks = resp.json()
        except Exception:
            pass

    if not jwks:
        raise ClerkTokenError(f"Failed to fetch Clerk JWKS from {jwks_url} or Clerk API")

    if not isinstance(jwks, dict) or not isinstance(jwks.get("keys"), list):
        raise ClerkTokenError("Invalid Clerk JWKS")
    keys = [key for key in jwks["keys"] if isinstance(key, dict)]
    target_key = None
    if key_id:
        target_key = next((k for k in keys if k.get("kid") == key_id), None)
    if not key_id and keys:
        target_key = next((k for k in keys if k.get("alg") in ("RS256", None)), keys[0])

    if not target_key or target_key.get("kty") != "RSA" or target_key.get("use", "sig") != "sig" or target_key.get("alg", "RS256") != "RS256":
        raise ClerkTokenError("No suitable RSA public key found in Clerk JWKS")

    try:
        jwk_obj = jwt.PyJWK.from_dict(target_key)
        pem = jwk_obj.key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("ascii")
    except Exception as exc:
        raise ClerkTokenError("Failed to convert Clerk JWK to PEM") from exc

    # Untrusted kid values must not grow the process cache without bound.
    if len(_JWKS_CACHE) >= 128:
        _JWKS_CACHE.pop(next(iter(_JWKS_CACHE)))
    _JWKS_CACHE[cache_key] = (now, pem)
    return pem


async def verify_clerk_session_auto(token: str) -> VerifiedClerkSession:
    """Verify a Clerk session JWT using environment config or JWKS auto-discovery."""
    settings = get_settings()
    issuer = settings.clerk_issuer.strip()
    if not issuer:
        raise ClerkTokenError("CLERK_ISSUER is not configured")

    kid = None
    try:
        header = jwt.get_unverified_header(token)
        if header.get("alg") != "RS256":
            raise ClerkTokenError("Unsupported Clerk signing algorithm")
        kid = header.get("kid")
        if kid is not None and (not isinstance(kid, str) or not kid or len(kid) > 128):
            raise ClerkTokenError("Invalid Clerk key identifier")
    except (jwt.PyJWTError, ValueError, TypeError) as exc:
        raise ClerkTokenError("Invalid Clerk session token") from exc

    public_key_pem = await get_or_fetch_clerk_public_key(issuer, kid)
    return verify_clerk_session(
        token,
        issuer=issuer,
        public_key_pem=public_key_pem,
        authorized_parties=settings.clerk_parties_tuple,
        audience=settings.clerk_audience.strip() or None,
    )
