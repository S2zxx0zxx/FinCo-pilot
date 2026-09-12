import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class BillingUsageCounter(Base):
    """Server-owned metered usage for resettable plan limits.

    One row represents one billing owner, one metric and one UTC calendar
    period. The browser never supplies or mutates these values. A subscription
    row lock serializes consumption before this row is updated, so retries and
    concurrent requests cannot both consume the last available unit.
    """

    __tablename__ = "billing_usage_counters"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "metric",
            "period_start",
            name="uq_billing_usage_user_metric_period",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    metric: Mapped[str] = mapped_column(String(64), index=True)
    period_start: Mapped[date] = mapped_column(Date, index=True)
    used: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
