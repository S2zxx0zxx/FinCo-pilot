import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LoanCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    principal: Decimal = Field(ge=1, le=Decimal("999999999999"), max_digits=14, decimal_places=2, allow_inf_nan=False)
    annual_rate: Decimal = Field(ge=0, le=60, max_digits=7, decimal_places=4, allow_inf_nan=False)
    term_months: int = Field(ge=1, le=600)
    first_due_date: date = Field(ge=date(2000, 1, 1), le=date(2100, 12, 31))
    currency: str = Field(default="INR", pattern=r"^[A-Z]{3}$")
    paid_installments: int = Field(default=0, ge=0, le=600)

    @model_validator(mode="after")
    def paid_within_term(self):
        if self.paid_installments > self.term_months:
            raise ValueError("Paid installments cannot exceed the loan term")
        return self


class LoanUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(ge=1)
    paid_installments: int = Field(ge=0, le=600)
    archived: bool = False


class LoanRead(LoanCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    version: int
    archived: bool
    updated_at: datetime


class LoanInstallment(BaseModel):
    number: int
    due_date: date
    payment: Decimal
    principal: Decimal
    interest: Decimal
    remaining_principal: Decimal
    reported_paid: bool


class LoanDetail(BaseModel):
    loan: LoanRead
    monthly_payment: Decimal
    total_interest: Decimal
    remaining_principal: Decimal
    schedule: list[LoanInstallment]
