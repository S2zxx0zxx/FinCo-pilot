"""No real Clerk account/network required. Cryptographic unit tests only."""
import time

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core.clerk_sessions import ClerkTokenError, verify_clerk_session


ISSUER = "https://fincopilot-test.clerk.accounts.dev"
PARTIES = ("http://localhost:3000", "https://fincopilot.app")


@pytest.fixture
def signing_keys():
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = private.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return private, public


def signed(private, **updates):
    now = int(time.time())
    payload = {
        "iss": ISSUER,
        "sub": "user_test123",
        "sid": "sess_test123",
        "azp": "http://localhost:3000",
        "iat": now,
        "nbf": now - 2,
        "exp": now + 120,
    }
    payload.update(updates)
    return jwt.encode(payload, private, algorithm="RS256")


def verify(token, public, **options):
    return verify_clerk_session(
        token,
        issuer=options.pop("issuer", ISSUER),
        public_key_pem=public,
        authorized_parties=options.pop("authorized_parties", PARTIES),
        **options,
    )


def test_accepts_genuine_rs256_clerk_session(signing_keys):
    private, public = signing_keys
    result = verify(signed(private), public)
    assert result.user_id == "user_test123"
    assert result.session_id == "sess_test123"


@pytest.mark.parametrize(
    "updates",
    [
        {"iss": "https://attacker.example"},
        {"exp": 1},
        {"nbf": int(time.time()) + 1000},
        {"azp": "https://attacker.example"},
        {"azp": None},
        {"sub": "not_a_clerk_id"},
        {"sid": ""},
        {"sts": "pending"},
        {"act": {"sub": "user_attacker"}},
    ],
)
def test_rejects_invalid_claims(signing_keys, updates):
    private, public = signing_keys
    with pytest.raises(ClerkTokenError):
        verify(signed(private, **updates), public)


def test_rejects_missing_required_session_claim(signing_keys):
    private, public = signing_keys
    now = int(time.time())
    token = jwt.encode(
        {"iss": ISSUER, "sub": "user_abc", "iat": now, "nbf": now, "exp": now + 60, "azp": PARTIES[0]},
        private,
        algorithm="RS256",
    )
    with pytest.raises(ClerkTokenError):
        verify(token, public)


def test_rejects_other_signing_key(signing_keys):
    private, public = signing_keys
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(ClerkTokenError):
        verify(signed(other_key), public)


def test_rejects_wrong_audience(signing_keys):
    private, public = signing_keys
    with pytest.raises(ClerkTokenError):
        verify(signed(private, aud="other-api"), public, audience="finco-api")


def test_rejects_hs256_algorithm(signing_keys):
    _, public = signing_keys
    token = jwt.encode(
        {"iss": ISSUER, "sub": "user_x", "sid": "sess_x", "azp": PARTIES[0]},
        "attacker-secret",
        algorithm="HS256",
    )
    with pytest.raises(ClerkTokenError):
        verify(token, public)


def test_rejects_missing_configuration(signing_keys):
    private, public = signing_keys
    with pytest.raises(ClerkTokenError):
        verify(signed(private), public, authorized_parties=())
    with pytest.raises(ClerkTokenError):
        verify(signed(private), public, issuer="http://insecure.local")
