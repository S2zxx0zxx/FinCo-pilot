import json

import pyotp
import pytest
from pydantic import SecretStr
from sqlalchemy import Text, bindparam, cast, select, text

from app.models.user import User

from app.core.config import get_settings
from app.core.mfa_secret import PREFIX, decrypt_seed, encrypt_seed
from scripts.seal_legacy_mfa_seeds import seal_batch


@pytest.mark.asyncio
async def test_seed_encrypted_in_actual_database_and_readable_in_orm(session, test_user):
    seed = pyotp.random_base32()
    test_user.totp_secret = seed
    await session.commit()
    raw = await session.scalar(select(cast(User.totp_secret, Text)).where(User.id == test_user.id))
    assert raw.startswith(PREFIX) and seed not in raw
    await session.refresh(test_user)
    assert test_user.totp_secret == seed


@pytest.mark.asyncio
async def test_legacy_sealing_is_bounded_non_destructive_and_idempotent(session, test_user):
    seed = pyotp.random_base32()
    epoch = test_user.auth_epoch
    await session.execute(text("UPDATE users SET totp_secret = :seed WHERE id = :id").bindparams(bindparam("id", type_=User.__table__.c.id.type)), {"seed": seed, "id": test_user.id})
    await session.commit()
    dry = await seal_batch(session, False, 1)
    assert dry["rows_encrypted"] == 0 and dry["legacy_rows_remaining"] == 1
    result = await seal_batch(session, True, 1)
    assert result["rows_encrypted"] == 1 and result["legacy_rows_remaining"] == 0
    await session.refresh(test_user)
    assert test_user.totp_secret == seed and test_user.auth_epoch == epoch
    assert (await seal_batch(session, True, 1))["rows_encrypted"] == 0


def test_key_rotation_requires_retained_key_and_never_returns_plaintext_on_failure(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "credential_encryption_key", SecretStr("synthetic-old-key"))
    seed = pyotp.random_base32()
    encrypted = encrypt_seed(seed)
    monkeypatch.setattr(settings, "credential_encryption_key", SecretStr("synthetic-new-key"))
    with pytest.raises(ValueError, match="Stored authenticator unavailable"):
        decrypt_seed(encrypted)
    monkeypatch.setattr(settings, "legacy_data_keys", SecretStr(json.dumps({"credentials": ["synthetic-old-key"]})))
    assert decrypt_seed(encrypted) == seed
    assert decrypt_seed(encrypt_seed(seed)) == seed


def test_corrupt_ciphertext_never_becomes_an_absent_second_factor():
    with pytest.raises(ValueError, match="Stored authenticator unavailable"):
        decrypt_seed(PREFIX + "invalid-ciphertext")


@pytest.mark.asyncio
async def test_existing_data_key_rotation_reseals_mfa_before_old_key_retirement(session, test_user, monkeypatch):
    from scripts.rotate_data_keys import rotate_data
    settings = get_settings()
    monkeypatch.setattr(settings, "credential_encryption_key", SecretStr("synthetic-before-key"))
    seed = pyotp.random_base32()
    epoch = test_user.auth_epoch
    test_user.totp_secret = seed
    await session.commit()
    before = await session.scalar(select(cast(User.totp_secret, Text)).where(User.id == test_user.id))
    monkeypatch.setattr(settings, "credential_encryption_key", SecretStr("synthetic-after-key"))
    monkeypatch.setattr(settings, "legacy_data_keys", SecretStr(json.dumps({"credentials": ["synthetic-before-key"]})))
    counts = await rotate_data(session, apply=True)
    await session.commit()
    assert counts["mfa_seeds"] == 1
    after = await session.scalar(select(cast(User.totp_secret, Text)).where(User.id == test_user.id))
    assert before != after
    monkeypatch.setattr(settings, "legacy_data_keys", SecretStr(""))
    await session.refresh(test_user)
    assert test_user.totp_secret == seed and test_user.auth_epoch == epoch
    with pytest.raises(ValueError):
        decrypt_seed(before)
