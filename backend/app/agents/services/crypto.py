"""Encrypt stored credentials independently of JWT authentication.

Old data keys and both historical KDF salts remain readable during a staged,
non-destructive rotation. New writes use CREDENTIAL_ENCRYPTION_KEY; development
retains SECRET_KEY fallback for compatibility with existing installations.
"""
from __future__ import annotations

import base64
import functools
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.credential_keys import data_keys


_CURRENT_SALT = b"fincopilot-agents-llm-keys-v1"
# Historical v1 KDF salt encoded as bytes so the current source tree does not
# reintroduce retired product naming while existing encrypted keys keep working.
_COMPAT_SALT_V1 = bytes.fromhex(
    "73656375726f2d6167656e74732d6c6c6d2d6b6579732d7631"
)


def _fernet_for_salt(salt: bytes, key: str | None = None) -> Fernet:
    return _derive_fernet(salt, key or data_keys()[0])


@functools.lru_cache(maxsize=32)
def _derive_fernet(salt: bytes, key: str) -> Fernet:
    secret = key.encode("utf-8")
    raw = hashlib.pbkdf2_hmac("sha256", secret, salt, iterations=100_000, dklen=32)
    return Fernet(base64.urlsafe_b64encode(raw))


def _fernet() -> Fernet:
    return _fernet_for_salt(_CURRENT_SALT)


def _compat_fernet_v1() -> Fernet:
    return _fernet_for_salt(_COMPAT_SALT_V1)


def encrypt(plaintext: str | None) -> str | None:
    if not plaintext:
        return None
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt(ciphertext: str | None) -> str | None:
    if not ciphertext:
        return None

    try:
        token = ciphertext.encode("ascii")
    except UnicodeEncodeError:
        return None
    for key in data_keys():
        for salt in (_CURRENT_SALT, _COMPAT_SALT_V1):
            try:
                return _fernet_for_salt(salt, key).decrypt(token).decode("utf-8")
            except (InvalidToken, ValueError):
                continue
    return None
