import uuid
import pytest
from app.core.auth import get_jwt_strategy
from app.models.workspace_deletion import WorkspaceDeletion
from app.models.workspace import WorkspaceMember
from app.services import workspace_deletion_service as service
from tests.test_workspace_deletion_workflow import target


@pytest.mark.asyncio
async def test_explicit_consent_freshness_receipt_cancel_and_unique_request(
    client, session, test_user, auth_headers
):
    workspace = await target(session, test_user)
    body = {"workspace_id": str(workspace.id), "confirmation": "DELETE THIS WORKSPACE"}
    legacy = await get_jwt_strategy().write_token(test_user)
    assert (
        await client.post(
            "/api/workspace-deletion", json=body, headers={"Authorization": f"Bearer {legacy}"}
        )
    ).status_code == 403
    assert (
        await client.post(
            "/api/workspace-deletion", json={**body, "confirmation": "yes"}, headers=auth_headers
        )
    ).status_code == 422
    response = await client.post("/api/workspace-deletion", json=body, headers=auth_headers)
    assert response.status_code == 202 and response.headers["cache-control"] == "no-store"
    data = response.json()
    job = await session.get(WorkspaceDeletion, uuid.UUID(data["id"]))
    assert data["tracking_token"] not in job.tracking_digest
    assert (
        await client.post("/api/workspace-deletion", json=body, headers=auth_headers)
    ).status_code == 409
    path = f"/api/workspace-deletion/{job.id}/status"
    assert (await client.get(path)).status_code == 404
    assert (
        await client.get(path, headers={"X-Deletion-Receipt": data["tracking_token"]})
    ).status_code == 200
    assert (
        await client.post(f"/api/workspace-deletion/{job.id}/cancel", headers=auth_headers)
    ).status_code == 200
    assert (
        await client.post("/api/workspace-deletion", json=body, headers=auth_headers)
    ).status_code == 202


@pytest.mark.asyncio
async def test_owner_detaches_manager_with_exact_confirmation_and_operator_gates(
    client, session, test_user, test_superuser, auth_headers
):
    workspace = await target(session, test_user)
    workspace.managed_by_user_id = test_superuser.id
    await session.commit()
    data = await service.request_deletion(session, test_user, workspace.id)
    body = {"confirmation": str(workspace.id), "evidence_sha256": "a" * 64}
    path = f"/api/workspace-deletion/{data['id']}/detach-manager"
    assert (
        await client.post(
            path, json={**body, "confirmation": str(uuid.uuid4())}, headers=auth_headers
        )
    ).status_code == 409
    assert (await client.post(path, json=body, headers=auth_headers)).status_code == 200
    await session.refresh(workspace)
    assert workspace.managed_by_user_id is None
    assert (
        await client.post(
            f"/api/workspace-deletion/operator/{data['id']}/execute", headers=auth_headers
        )
    ).status_code == 403
    assert (
        await client.get("/api/workspace-deletion/operator/requests", headers=auth_headers)
    ).status_code == 403


@pytest.mark.asyncio
async def test_current_payer_cannot_be_stolen_by_owner(
    client, session, test_user, test_superuser, auth_headers
):
    workspace = await target(session, test_user)
    workspace.billing_owner_user_id = test_superuser.id
    session.add(WorkspaceMember(workspace_id=workspace.id, user_id=test_superuser.id, role="owner"))
    await session.commit()
    data = await service.request_deletion(session, test_user, workspace.id)
    body = {"confirmation": str(workspace.id), "evidence_sha256": "a" * 64}
    assert (
        await client.post(
            f"/api/workspace-deletion/{data['id']}/transfer-billing",
            json=body,
            headers=auth_headers,
        )
    ).status_code == 403
    await session.refresh(workspace)
    assert workspace.billing_owner_user_id == test_superuser.id


@pytest.mark.asyncio
async def test_null_billing_repair_requires_independent_fresh_operator(
    client, session, test_user, test_superuser, auth_headers
):
    workspace = await target(session, test_user)
    workspace.billing_owner_user_id = None
    await session.commit()
    result = await service.request_deletion(session, test_user, workspace.id)
    path = f"/api/workspace-deletion/operator/{result['id']}/repair-billing"
    body = {"confirmation": str(workspace.id), "evidence_sha256": "a" * 64}
    assert (await client.post(path, json=body, headers=auth_headers)).status_code == 403
    token = await get_jwt_strategy().write_token(test_superuser, fresh_auth=True)
    headers = {"Authorization": f"Bearer {token}"}
    assert (await client.post(path, json=body, headers=headers)).status_code == 200
    await session.refresh(workspace)
    assert workspace.billing_owner_user_id == test_user.id
    assert (await client.post(path, json=body, headers=headers)).status_code == 409


@pytest.mark.asyncio
async def test_current_actual_payer_transfers_without_changing_global_subscription(
    client, session, test_user, test_superuser
):
    from app.models.subscription import Subscription
    from sqlalchemy import select

    workspace = await target(session, test_user)
    workspace.billing_owner_user_id = test_superuser.id
    session.add(WorkspaceMember(workspace_id=workspace.id, user_id=test_superuser.id, role="owner"))
    await session.commit()
    result = await service.request_deletion(session, test_user, workspace.id)
    token = await get_jwt_strategy().write_token(test_superuser, fresh_auth=True)
    response = await client.post(
        f"/api/workspace-deletion/{result['id']}/transfer-billing",
        json={"confirmation": str(workspace.id), "evidence_sha256": "a" * 64},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    await session.refresh(workspace)
    assert workspace.billing_owner_user_id == test_user.id
    assert await session.scalar(select(Subscription.id).where(Subscription.user_id == test_user.id))
