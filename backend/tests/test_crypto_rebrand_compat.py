"""Compatibility coverage for provider-key encryption across identity migration."""

import base64
import hashlib

from cryptography.fernet import Fernet

from app.agents.services.crypto import decrypt
from app.core.config import get_settings


def test_decrypts_pre_rebrand_provider_key() -> None:
    """Stored credentials from before the rename must remain readable."""
    compat_salt = bytes.fromhex(
        "73656375726f2d6167656e74732d6c6c6d2d6b6579732d7631"
    )
    secret_key = get_settings().secret_key.get_secret_value().encode("utf-8")
    raw = hashlib.pbkdf2_hmac(
        "sha256", secret_key, compat_salt, iterations=100_000, dklen=32
    )
    legacy_cipher = Fernet(base64.urlsafe_b64encode(raw))

    token = legacy_cipher.encrypt(b"provider-key-still-readable").decode("ascii")

    assert decrypt(token) == "provider-key-still-readable"
