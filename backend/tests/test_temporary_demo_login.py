"""Explicit opt-in demo login never authenticates or exposes real users."""
import pytest
from httpx import AsyncClient

from app.core.config import get_settings


@pytest.fixture
def temporary_demo_settings():
    settings = get_settings()
    fields = ("temporary_demo_login_enabled", "deployment_environment", "database_url", "frontend_url", "local_auth_enabled")
    previous = {field: getattr(settings, field) for field in fields}
    settings.temporary_demo_login_enabled = True
    settings.deployment_environment = "development"
    settings.database_url = "postgresql+asyncpg://postgres:postgres@localhost:5432/fincopilot_demo"
    settings.frontend_url = "http://localhost:5173"
    settings.local_auth_enabled = True
    yield settings
    for field, value in previous.items():
        setattr(settings, field, value)


def credentials(username="anything", password="anything"):
    return {"username": username, "password": password}


@pytest.mark.asyncio
async def test_demo_login_is_disabled_by_default(client: AsyncClient, clean_db):
    response = await client.post("/api/auth/login", data=credentials())
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_arbitrary_credentials_only_open_an_isolated_nonadmin_demo_user(
    client: AsyncClient, test_user, temporary_demo_settings,
):
    first = await client.post(
        "/api/auth/login",
        data=credentials("random-text", "random-text"),
        headers={"Origin": "http://localhost:5173"},
    )
    second = await client.post(
        "/api/auth/login",
        data=credentials("someone-else@example.com", "even-another-password"),
        headers={"Origin": "http://localhost:5173"},
    )
    assert first.status_code == second.status_code == 200
    assert first.json()["access_token"] != second.json()["access_token"] or first.json()["access_token"]

    me = await client.get(
        "/api/users/me",
        headers={"Authorization": f'Bearer {first.json()["access_token"]}'},
    )
    assert me.status_code == 200
    assert me.json()["email"] == "finco-temporary-demo@example.com"
    assert me.json()["id"] != str(test_user.id)
    assert me.json()["is_superuser"] is False
    assert me.json()["is_active"] is True


@pytest.mark.asyncio
async def test_no_local_origin_means_real_login_not_bypassed(
    client: AsyncClient, test_user, temporary_demo_settings,
):
    for origin in ({}, {"Origin": "https://attacker.example"}):
        response = await client.post("/api/auth/login", data=credentials(), headers=origin)
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_demo_rejected_in_non_development_and_remote_database(
    client: AsyncClient, clean_db, temporary_demo_settings,
):
    s = temporary_demo_settings
    for env, db in (
        ("staging", "postgresql+asyncpg://localhost/fincopilot_demo"),
        ("production", "postgresql+asyncpg://localhost/fincopilot_demo"),
        ("test", "postgresql+asyncpg://localhost/fincopilot_demo"),
        ("development", "postgresql+asyncpg://remote.example/fincopilot_demo"),
    ):
        s.deployment_environment, s.database_url = env, db
        response = await client.post(
            "/api/auth/login",
            data=credentials(),
            headers={"Origin": "http://localhost:5173"},
        )
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_disabling_demo_mode_revokes_issued_tokens(
    client: AsyncClient, clean_db, temporary_demo_settings,
):
    issued = await client.post(
        "/api/auth/login",
        data=credentials(),
        headers={"Origin": "http://localhost:5173"},
    )
    assert issued.status_code == 200
    headers = {"Authorization": f'Bearer {issued.json()["access_token"]}'}
    assert (await client.get("/api/users/me", headers=headers)).status_code == 200
    temporary_demo_settings.temporary_demo_login_enabled = False
    assert (await client.get("/api/users/me", headers=headers)).status_code == 401


@pytest.mark.asyncio
async def test_demo_logout_rotates_token_and_relogin_still_works(
    client: AsyncClient, clean_db, temporary_demo_settings,
):
    headers = {"Origin": "http://localhost:5173"}
    issued = await client.post("/api/auth/login", data=credentials(), headers=headers)
    assert issued.status_code == 200
    old_headers = {"Authorization": f'Bearer {issued.json()["access_token"]}'}
    assert (await client.post("/api/auth/logout", headers=old_headers)).status_code == 200
    assert (await client.get("/api/users/me", headers=old_headers)).status_code == 401
    renewed = await client.post("/api/auth/login", data=credentials(), headers=headers)
    assert renewed.status_code == 200
    assert (await client.get(
        "/api/users/me",
        headers={"Authorization": f'Bearer {renewed.json()["access_token"]}'},
    )).status_code == 200


@pytest.mark.asyncio
async def test_demo_does_not_take_over_preexisting_account(
    client: AsyncClient, clean_db, temporary_demo_settings,
):
    # A user who registered the reserved email beforehand is not adopted.
    registered = await client.post(
        "/api/auth/register",
        json={"email": "finco-temporary-demo@example.com", "password": "validPassword123"},
    )
    assert registered.status_code == 201
    result = await client.post(
        "/api/auth/login",
        data=credentials(),
        headers={"Origin": "http://localhost:5173"},
    )
    assert result.status_code == 409
    assert result.json()["detail"] == "DEVELOPMENT_DEMO_ACCOUNT_CONFLICT"
