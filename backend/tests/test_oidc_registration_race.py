import asyncio
import json
import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from fastapi_users.db import SQLAlchemyUserDatabase
from fastapi_users.exceptions import UserAlreadyExists

from app.api import oidc_auth
from app.core.auth import UserManager
from app.models.user import User
from tests.test_oidc_auth import FakeRedis, oidc_settings as oidc_settings


@pytest.mark.parametrize("identity", ["local", "different", "same", "inactive"])
@pytest.mark.parametrize("conflict", ["manager", "database"])
async def test_registration_conflict_rechecks_identity_and_preserves_existing_preferences(
    session, clean_db, oidc_settings, monkeypatch, identity, conflict
):
    oidc_settings.oidc_existing_user_link_mode = "disabled"
    issuer = "https://id.example.com"
    original_preferences = {"display_name": "Keep existing profile", "language": "hi"}
    raced = User(
        id=uuid.uuid4(), email="synthetic-race@example.com", hashed_password="synthetic-unused-hash",
        is_active=identity != "inactive", is_verified=True, is_superuser=False, preferences=original_preferences,
        oidc_issuer=issuer if identity in {"same", "inactive"} else "https://other.example" if identity == "different" else None,
        oidc_subject="incoming-sub" if identity in {"same", "inactive"} else "other-sub" if identity == "different" else None,
    )
    expected_identity = (raced.oidc_issuer, raced.oidc_subject)
    manager = UserManager(SQLAlchemyUserDatabase(session, User))

    async def create_conflict(*args, **kwargs):
        # The row becomes visible after the initial email lookup, reproducing
        # another request winning registration without a live provider.
        session.add(raced)
        await session.commit()
        if conflict == "manager":
            raise UserAlreadyExists()
        # Exercise an actual failed unique-email transaction, not a mocked
        # exception: recovery must rollback before querying the winning row.
        session.add(User(id=uuid.uuid4(), email=raced.email, hashed_password="synthetic-unused-hash",
                         is_active=True, is_verified=True, is_superuser=False))
        await session.commit()
        raise AssertionError("Duplicate email unexpectedly committed")

    monkeypatch.setattr(manager, "create", create_conflict)
    seed = AsyncMock()
    monkeypatch.setattr(oidc_auth, "create_personal_workspace_for_user", seed)
    claims = {"sub": "incoming-sub", "email": raced.email, "email_verified": True, "name": "Do not overwrite"}
    if identity == "same":
        result = await oidc_auth._get_or_create_oidc_user(claims, {}, issuer, session, manager)
        assert result.id == raced.id
    else:
        with pytest.raises(HTTPException) as exc:
            await oidc_auth._get_or_create_oidc_user(claims, {}, issuer, session, manager)
        assert exc.value.status_code == 403
    await session.refresh(raced)
    assert (raced.oidc_issuer, raced.oidc_subject) == expected_identity
    assert raced.preferences == original_preferences
    seed.assert_not_awaited()


async def test_callback_state_is_single_use_under_concurrent_consumers():
    redis = FakeRedis()
    original = json.dumps({"nonce": "synthetic-nonce", "code_verifier": "synthetic-verifier"})
    await redis.set("oidc_state:synthetic", original)
    results = await asyncio.gather(*(oidc_auth._consume_oidc_state(redis, "synthetic") for _ in range(32)))
    assert results.count(original) == 1 and results.count(None) == 31
    assert await oidc_auth._consume_oidc_state(redis, "synthetic") is None
