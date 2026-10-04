"""Purpose-separated encryption for stored authenticator seeds, with staged key rotation."""
import base64
import functools

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlalchemy.types import Text, TypeDecorator

from app.core.credential_keys import data_keys

PREFIX = "mfa:v1:"


@functools.lru_cache(maxsize=32)
def _cipher(key: str) -> Fernet:
    derived = HKDF(algorithm=hashes.SHA256(), length=32, salt=b"fincopilot-mfa-seed-v1", info=b"authenticator-encryption").derive(key.encode())
    return Fernet(base64.urlsafe_b64encode(derived))


def encrypt_seed(seed: str | None) -> str | None:
    return PREFIX + _cipher(data_keys()[0]).encrypt(seed.encode()).decode("ascii") if seed else None


def decrypt_seed(value: str | None) -> str | None:
    if not value:
        return None
    if not value.startswith(PREFIX):
        # Read-only compatibility for seeds created before the widening migration.
        # New ORM writes always encrypt; explicit operator conversion seals legacy rows.
        return value
    token = value[len(PREFIX):].encode()
    for key in data_keys():
        try:
            return _cipher(key).decrypt(token).decode()
        except (InvalidToken, ValueError, UnicodeDecodeError):
            continue
    raise ValueError("Stored authenticator unavailable; encryption key or data invalid")


class EncryptedMFASeed(TypeDecorator[str]):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return encrypt_seed(value)

    def process_result_value(self, value, dialect):
        return decrypt_seed(value)
