from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class SpendingPlanRequest(BaseModel):
    horizon_days: int = Field(default=30, ge=1, le=90)
    emergency_buffer: Decimal = Field(default=Decimal(0), ge=0, le=Decimal('999999999999'), allow_inf_nan=False)
    goal_reserve: Decimal = Field(default=Decimal(0), ge=0, le=Decimal('999999999999'), allow_inf_nan=False)
    other_obligations: Decimal = Field(default=Decimal(0), ge=0, le=Decimal('999999999999'), allow_inf_nan=False)
    obligations_reviewed: bool = False


class SpendingPlan(BaseModel):
    currency: str
    as_of: date
    through: date
    status: str
    cash_balance: Decimal
    card_debt_reserve: Decimal
    upcoming_outflows: Decimal
    loan_due_reserve: Decimal = Decimal(0)
    emergency_buffer: Decimal
    goal_reserve: Decimal
    other_obligations: Decimal
    safe_to_spend: Decimal | None
    daily_allowance: Decimal | None
    shortfall: Decimal | None
    blockers: list[str]
    assumptions: list[str]
