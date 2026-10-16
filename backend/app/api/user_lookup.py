"""User lookup for group invites.

Two modes:
- ``/lookup`` — exact-match by email, used to validate a typed address
  before creating a member.
- ``/directory`` — flat list of all users on the instance, used to power
  the "pick an existing user" dropdown when adding a member.

The directory defaults to active users sharing an active workspace with the
caller (including its explicit manager). A trusted self-hosted operator may
explicitly choose instance scope. Exact-email lookup remains available for
invitations; it is not an enumerable instance directory.

"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, EmailStr
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_active_user
from app.core.config import get_settings
from app.core.database import get_async_session
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember

router = APIRouter(prefix="/api/users", tags=["users"])


class UserLookupResult(BaseModel):
    id: uuid.UUID
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)


@router.get("/lookup", response_model=UserLookupResult)
async def lookup_user_by_email(
    email: EmailStr = Query(..., description="Exact email to look up"),
    session: AsyncSession = Depends(get_async_session),
    _: User = Depends(current_active_user),
):
    result = await session.execute(
        select(User).where(func.lower(User.email) == email.lower())
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.get("/directory", response_model=list[UserLookupResult])
async def list_users_directory(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    """List permitted collaborators; never enumerate unrelated accounts by default."""
    query = select(User).where(User.is_active.is_(True))
    if get_settings().user_directory_scope != "instance":
        memberships = select(WorkspaceMember.workspace_id).where(WorkspaceMember.user_id == user.id).correlate(None)
        workspaces = select(Workspace.id).where(
            Workspace.is_archived.is_(False),
            or_(Workspace.id.in_(memberships), Workspace.managed_by_user_id == user.id),
        ).correlate(None)
        peers = select(WorkspaceMember.user_id).where(WorkspaceMember.workspace_id.in_(workspaces)).correlate(None)
        managers = select(Workspace.managed_by_user_id).where(Workspace.id.in_(workspaces)).correlate(None)
        # Bind typed UUIDs to User.id, as workspace_service.list_members does.
        # Its GUID representation can differ from workspace UUID columns on
        # SQLite; do not compare their raw storage strings or cast DB indexes.
        visible_ids = {user.id, *(await session.scalars(peers)).all()}
        visible_ids.update(identity for identity in (await session.scalars(managers)).all() if identity)
        query = query.where(User.id.in_(visible_ids))
    result = await session.execute(query.order_by(User.email))
    return list(result.scalars().all())
