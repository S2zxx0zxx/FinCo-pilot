import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class Loan(Base):
    """User-entered fixed-rate repayment plan; payment counts are self-reported."""

    __tablename__ = "loans"
    __table_args__ = (
        CheckConstraint("principal >= 1 AND principal <= 999999999999", name="ck_loans_principal"),
        CheckConstraint("annual_rate >= 0 AND annual_rate <= 60", name="ck_loans_rate"),
        CheckConstraint("term_months >= 1 AND term_months <= 600", name="ck_loans_term"),
        CheckConstraint("paid_installments >= 0 AND paid_installments <= term_months", name="ck_loans_paid"),
        CheckConstraint("version >= 1", name="ck_loans_version"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(120))
    principal: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    annual_rate: Mapped[Decimal] = mapped_column(Numeric(7, 4))
    term_months: Mapped[int] = mapped_column(Integer)
    first_due_date: Mapped[date] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(3))
    paid_installments: Mapped[int] = mapped_column(Integer, default=0)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
