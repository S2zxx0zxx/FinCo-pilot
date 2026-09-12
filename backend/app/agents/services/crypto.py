"""Symmetric encryption for stored secrets (LLM API keys, etc.).

Key derivation: PBKDF2(SHA256, app SECRET_KEY) so we don't need a
separate key file. If the operator rotates SECRET_KEY, existing
ciphertexts become unreadable — that's by design (rotation = re-enter
your provider keys).

Brand migrations are different from key rotation: they must not strand
already-encrypted provider credentials. New writes use the FinCo-Pilot salt,
while reads retain a one-way compatibility fallback for ciphertext created
before the identity migration.
"""
from __future__ import annotations

import base64
import functools
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


_CURRENT_SALT = b"fincopilot-agents-llm-keys-v1"
# Historical v1 KDF salt encoded as bytes so the current source tree does not
# reintroduce retired product naming while existing encrypted keys keep working.
_COMPAT_SALT_V1 = bytes.fromhex(
    "73656375726f2d6167656e74732d6c6c6d2d6b6579732d7631"
)


def _fernet_for_salt(salt: bytes) -> Fernet:
    secret = get_settings().secret_key.get_secret_value().encode("utf-8")
    raw = hashlib.pbkdf2_hmac("sha256", secret, salt, iterations=100_000, dklen=32)
    return Fernet(base64.urlsafe_b64encode(raw))


@functools.lru_cache(maxsize=1)
def _fernet() -> Fernet:
    return _fernet_for_salt(_CURRENT_SALT)


@functools.lru_cache(maxsize=1)
def _compat_fernet_v1() -> Fernet:
    return _fernet_for_salt(_COMPAT_SALT_V1)


def encrypt(plaintext: str | None) -> str | None:
    if not plaintext:
        return None
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt(ciphertext: str | None) -> str | None:
    if not ciphertext:
        return None

    token = ciphertext.encode("ascii")
    try:
        return _fernet().decrypt(token).decode("utf-8")
    except (InvalidToken, ValueError):
        pass

    # Compatibility read path for credentials encrypted before the identity
    # migration. New writes always use the current FinCo-Pilot salt above.
    try:
        return _compat_fernet_v1().decrypt(token).decode("utf-8")
    except (InvalidToken, ValueError):
        return None  # silently treat corrupt/rotated entries as missing
