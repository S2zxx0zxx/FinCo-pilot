import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.catalog import get_plan_spec
from app.billing.enums import Capability, PlanId
from app.billing.errors import EntitlementRequiredError
from app.billing.service import get_effective_plan, minimum_plan_for_capability
from app.models.workspace import Workspace


async def require_user_capability(
    session: AsyncSession,
    user_id: uuid.UUID,
    capability: Capability,
) -> PlanId:
    plan = await get_effective_plan(session, user_id)
    if not get_plan_spec(plan).has(capability):
        error = EntitlementRequiredError(
            capability=capability,
            current_plan=plan,
            required_plan=minimum_plan_for_capability(capability),
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error.detail())
    return plan


async def require_workspace_capability(
    session: AsyncSession,
    workspace: Workspace,
    capability: Capability,
) -> PlanId:
    """Gate a workspace feature using its explicit billing owner.

    A malformed legacy workspace with no billing owner fails closed as Free;
    it never borrows the acting member's subscription implicitly.
    """
    owner_id = workspace.billing_owner_user_id
    plan = await get_effective_plan(session, owner_id) if owner_id is not None else PlanId.FREE
    if not get_plan_spec(plan).has(capability):
        error = EntitlementRequiredError(
            capability=capability,
            current_plan=plan,
            required_plan=minimum_plan_for_capability(capability),
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error.detail())
    return plan
