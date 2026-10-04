"""Verify bootstrap rollback, permanent closure and operator secret handling."""
import json
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import func, select

from app.core.auth import UserManager
from app.models.app_settings import AppSetting
from app.models.user import User
from app.services.admin_bootstrap_service import BOOTSTRAP_RECORD_KEY, CreateAdminRequest, provision_first_admin
from fastapi_users.db import SQLAlchemyUserDatabase


@pytest.mark.asyncio
async def test_seed_failure_rolls_back_and_allows_retry(session, clean_db, monkeypatch):
    manager = UserManager(SQLAlchemyUserDatabase(session, User))
    body = CreateAdminRequest(email="operator@example.com", password="StrongPass123!", language="en")
    from app.services import rule_service
    original = rule_service.create_default_rules
    monkeypatch.setattr(rule_service, "create_default_rules", AsyncMock(side_effect=RuntimeError("seed failed")))
    with pytest.raises(RuntimeError, match="seed failed"):
        await provision_first_admin(session, manager, body)
    await session.rollback()
    assert await session.scalar(select(func.count(User.id))) == 0
    assert await session.get(AppSetting, BOOTSTRAP_RECORD_KEY) is None
    from app.core.database import Base
    for table in Base.metadata.sorted_tables:
        assert await session.scalar(select(func.count()).select_from(table)) == 0, table.name
    monkeypatch.setattr(rule_service, "create_default_rules", original)
    user = await provision_first_admin(session, manager, body)
    await session.commit()
    assert user.is_superuser and user.is_active and not user.is_verified
    assert manager.password_helper.verify_and_update("StrongPass123!", user.hashed_password)[0]
    record = await session.get(AppSetting, BOOTSTRAP_RECORD_KEY)
    assert json.loads(record.value)["user_id"] == str(user.id)
    assert body.email not in record.value
    assert body.password.get_secret_value() not in record.value


@pytest.mark.asyncio
async def test_permanent_record_closes_empty_database(client, session, clean_db):
    session.add(AppSetting(key=BOOTSTRAP_RECORD_KEY, value='{"event":"first_admin_bootstrapped"}'))
    await session.commit()
    status = await client.get("/api/setup/status")
    assert not status.json()["has_users"]
    assert not status.json()["setup_available"]
    response = await client.post("/api/setup/create-admin", json={"email":"operator@example.com", "password":"StrongPass123!"})
    assert response.status_code == 403
    assert await session.scalar(select(func.count(User.id))) == 0


def test_password_file_rejects_public_permissions_and_symlink(tmp_path):
    from scripts.bootstrap_first_admin import password_from_file
    secret = tmp_path / "password"
    secret.write_text("secret password\n")
    secret.chmod(0o600)
    assert password_from_file(str(secret)) == "secret password"
    secret.chmod(0o644)
    with pytest.raises(ValueError):
        password_from_file(str(secret))
    link = tmp_path / "link"
    link.symlink_to(secret)
    with pytest.raises(OSError):
        password_from_file(str(link))


@pytest.mark.asyncio
async def test_protected_token_and_password_policy(client, session, clean_db, monkeypatch):
    from app.core.config import get_settings
    from pydantic import SecretStr
    settings = get_settings()
    monkeypatch.setattr(settings, "deployment_environment", "staging")
    monkeypatch.setattr(settings, "setup_token", SecretStr("x" * 40))
    payload = {"email": "operator@example.com", "password": "StrongPass123!"}
    for token in ("", "wrong"):
        response = await client.post("/api/setup/create-admin", json=payload, headers={"X-Setup-Token": token})
        assert response.status_code == 404
    response = await client.post("/api/setup/create-admin", json=payload, headers={"X-Setup-Token": "x" * 40})
    assert response.status_code == 400
    assert await session.scalar(select(func.count(User.id))) == 0
    payload["password"] = "A-long-enough-password"
    response = await client.post("/api/setup/create-admin", json=payload, headers={"X-Setup-Token": "x" * 40})
    assert response.status_code == 200
    assert (await client.get("/api/setup/status")).json()["minimum_password_length"] == 15


@pytest.mark.asyncio
async def test_production_registration_waits_for_admin(client, clean_db, monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "deployment_environment", "production")
    response = await client.post("/api/auth/register", json={"email": "public@example.com", "password": "StrongPass123!", "is_superuser": True})
    assert response.status_code == 409


def test_password_file_rejects_fifo_without_waiting(tmp_path):
    import os
    from scripts.bootstrap_first_admin import password_from_file
    fifo = tmp_path / "fifo"
    os.mkfifo(fifo, 0o600)
    with pytest.raises(ValueError):
        password_from_file(str(fifo))


@pytest.mark.parametrize("environment", ["STAGING", " production ", "staging "])
def test_protected_password_minimum_normalizes_environment(monkeypatch, environment):
    from app.core.config import get_settings
    from app.services.admin_bootstrap_service import minimum_password_length
    monkeypatch.setattr(get_settings(), "deployment_environment", environment)
    assert minimum_password_length() == 15
