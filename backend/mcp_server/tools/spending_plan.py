from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.spending_plan import SpendingPlanRequest
from app.services.spending_plan_service import calculate_spending_plan
from mcp_server.auth import CallContext
from mcp_server.registry import tool
from mcp_server.tools._helpers import num, resolve_workspace_id


@tool(
    name="get_safe_to_spend",
    description=(
        "Calculate FinCo-Pilot's deterministic Safe-to-Spend estimate for the current "
        "workspace. This is the source of truth for the headline amount; do not "
        "recalculate it in the LLM. Returns blockers instead of inventing a number "
        "when balances, obligations, bank freshness, account classification, or FX "
        "data are not safe enough."
    ),
    parameters={
        "type": "object",
        "properties": {
            "horizon_days": {"type": "integer", "minimum": 1, "maximum": 90, "default": 30},
            "emergency_buffer": {"type": "number", "minimum": 0, "default": 0},
            "goal_reserve": {"type": "number", "minimum": 0, "default": 0},
            "other_obligations": {"type": "number", "minimum": 0, "default": 0},
            "obligations_reviewed": {
                "type": "boolean",
                "default": False,
                "description": (
                    "True only when the user explicitly confirmed balances, bills, "
                    "loan repayments and other obligations are reviewed."
                ),
            },
        },
        "additionalProperties": False,
    },
    tags=["read", "spending_plan", "safe_to_spend"],
)
async def get_safe_to_spend(
    *,
    session: AsyncSession,
    ctx: CallContext,
    horizon_days: int = 30,
    emergency_buffer: float = 0,
    goal_reserve: float = 0,
    other_obligations: float = 0,
    obligations_reviewed: bool = False,
) -> dict[str, Any]:
    workspace_id = await resolve_workspace_id(session, ctx)
    request = SpendingPlanRequest(
        horizon_days=int(horizon_days),
        emergency_buffer=Decimal(str(emergency_buffer)),
        goal_reserve=Decimal(str(goal_reserve)),
        other_obligations=Decimal(str(other_obligations)),
        obligations_reviewed=bool(obligations_reviewed),
    )
    plan = await calculate_spending_plan(
        session, workspace_id, ctx.user_id, request
    )
    return {
        "currency": plan.currency,
        "as_of": plan.as_of.isoformat(),
        "through": plan.through.isoformat(),
        "status": plan.status,
        "cash_balance": num(plan.cash_balance),
        "card_debt_reserve": num(plan.card_debt_reserve),
        "upcoming_outflows": num(plan.upcoming_outflows),
        "loan_due_reserve": num(plan.loan_due_reserve),
        "emergency_buffer": num(plan.emergency_buffer),
        "goal_reserve": num(plan.goal_reserve),
        "other_obligations": num(plan.other_obligations),
        "safe_to_spend": num(plan.safe_to_spend),
        "daily_allowance": num(plan.daily_allowance),
        "shortfall": num(plan.shortfall),
        "blockers": list(plan.blockers),
        "assumptions": list(plan.assumptions),
    }
