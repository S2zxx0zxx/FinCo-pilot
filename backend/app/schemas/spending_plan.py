import uuid
from typing import Literal

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ManualBalanceConfirmation(BaseModel):
    """User-entered current amount, not bank verification or a ledger mutation."""
    model_config = ConfigDict(extra="forbid")
    amount: Decimal = Field(ge=Decimal('-999999999999'), le=Decimal('999999999999'),
                            max_digits=14, decimal_places=2, allow_inf_nan=False)
    currency: str = Field(pattern=r'^[A-Z]{3}$')
    kind: Literal['cash', 'card_debt']
    as_of: date

    @model_validator(mode='after')
    def validate_debt(self):
        if self.kind == 'card_debt' and self.amount < 0:
            raise ValueError('Card debt must be a non-negative outstanding amount')
        return self


class SpendingPlanRequest(BaseModel):
    horizon_days: int = Field(default=30, ge=1, le=90)
    emergency_buffer: Decimal = Field(default=Decimal(0), ge=0, le=Decimal('999999999999'), allow_inf_nan=False)
    goal_reserve: Decimal = Field(default=Decimal(0), ge=0, le=Decimal('999999999999'), allow_inf_nan=False)
    other_obligations: Decimal = Field(default=Decimal(0), ge=0, le=Decimal('999999999999'), allow_inf_nan=False)
    obligations_reviewed: bool = False
    manual_balances: dict[uuid.UUID, ManualBalanceConfirmation] = Field(default_factory=dict, max_length=1000)


class SpendingPlan(BaseModel):
    currency: str
    as_of: date
    through: date
    status: str
    cash_balance: Decimal | None
    card_debt_reserve: Decimal | None
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
