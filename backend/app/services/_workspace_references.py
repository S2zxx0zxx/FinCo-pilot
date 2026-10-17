"""Authorize request-supplied relationships before writes or provider I/O."""

import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def require_workspace_reference(
    session: AsyncSession,
    model: Any,
    identity: uuid.UUID | None,
    workspace_id: uuid.UUID,
    detail: str,
) -> None:
    # An omitted/null optional relationship retains the existing unlink flow.
    if identity is None:
        return
    found = await session.scalar(
        select(model.id).where(
            model.id == identity,
            model.workspace_id == workspace_id,
        )
    )
    if found is None:
        # Foreign and nonexistent identities have exactly the same contract.
        raise HTTPException(400, detail)
