import pytest


@pytest.mark.asyncio
async def test_lookup_existing_user(client, auth_headers, test_user):
    resp = await client.get(
        "/api/users/lookup",
        params={"email": test_user.email},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"].lower() == test_user.email.lower()
    assert body["id"] == str(test_user.id)


@pytest.mark.asyncio
async def test_lookup_case_insensitive(client, auth_headers, test_user):
    resp = await client.get(
        "/api/users/lookup",
        params={"email": test_user.email.upper()},
        headers=auth_headers,
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_lookup_missing_user(client, auth_headers, test_user):
    resp = await client.get(
        "/api/users/lookup",
        params={"email": "nobody@example.org"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_lookup_requires_auth(client):
    resp = await client.get(
        "/api/users/lookup", params={"email": "anyone@example.com"}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_directory_hides_unrelated_account_emails(client, auth_headers, session, test_user):
    import uuid
    from app.models.user import User

    stranger = User(id=uuid.uuid4(), email='unrelated-directory@example.org',
                    hashed_password='synthetic-not-for-login', is_active=True, is_verified=True)
    session.add(stranger)
    await session.commit()
    response = await client.get('/api/users/directory', headers=auth_headers)
    assert response.status_code == 200
    assert {row['id'] for row in response.json()} == {str(test_user.id)}


@pytest.mark.asyncio
async def test_directory_preserves_shared_member_and_manager_visibility_but_not_archive(
    client, auth_headers, session, test_user, test_workspace,
):
    import uuid
    from app.models.user import User
    from app.models.workspace import WorkspaceMember

    teammate = User(id=uuid.uuid4(), email='shared-directory@example.org',
                    hashed_password='synthetic-not-for-login', is_active=True, is_verified=True)
    manager = User(id=uuid.uuid4(), email='manager-directory@example.org',
                   hashed_password='synthetic-not-for-login', is_active=True, is_verified=True)
    session.add_all([teammate, manager])
    await session.flush()
    session.add(WorkspaceMember(workspace_id=test_workspace.id, user_id=teammate.id, role='viewer'))
    test_workspace.managed_by_user_id = manager.id
    await session.commit()
    response = await client.get('/api/users/directory', headers=auth_headers)
    assert {x['id'] for x in response.json()} == {str(test_user.id), str(teammate.id), str(manager.id)}
    test_workspace.is_archived = True
    await session.commit()
    response = await client.get('/api/users/directory', headers=auth_headers)
    assert {x['id'] for x in response.json()} == {str(test_user.id)}


@pytest.mark.asyncio
async def test_directory_instance_scope_requires_explicit_operator_opt_in(
    client, auth_headers, session, monkeypatch,
):
    import uuid
    from app.core.config import get_settings
    from app.models.user import User

    stranger = User(id=uuid.uuid4(), email='explicit-instance@example.org',
                    hashed_password='synthetic-not-for-login', is_active=True, is_verified=True)
    session.add(stranger)
    await session.commit()
    monkeypatch.setattr(get_settings(), 'user_directory_scope', 'instance')
    response = await client.get('/api/users/directory', headers=auth_headers)
    assert str(stranger.id) in {row['id'] for row in response.json()}


@pytest.mark.asyncio
async def test_directory_requires_auth(client):
    assert (await client.get('/api/users/directory')).status_code == 401
