"""Durable deletion receipts, distinct from application identity and financial rows."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class WorkspaceDeletion(Base):
    __tablename__ = "workspace_deletions"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(index=True)
    requester_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    # NULL after cancellation permits a new request. Completed tombstones stay unique.
    active_workspace_id: Mapped[uuid.UUID | None] = mapped_column(unique=True, nullable=True)
    tracking_digest: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(32), default="requested")
    blockers: Mapped[list] = mapped_column(JSON, default=list)
    manifest: Mapped[dict] = mapped_column(JSON, default=dict)
    review: Mapped[dict] = mapped_column(JSON, default=dict)
    receipts: Mapped[dict] = mapped_column(JSON, default=dict)
    lease_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    primary_deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkspaceDeletionHold(Base):
    __tablename__ = "workspace_deletion_holds"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(index=True)
    evidence_sha256: Mapped[str] = mapped_column(String(64))
    # Codes only, never legal narratives, identity documents, or provider secrets.
    reason: Mapped[str] = mapped_column(String(40))
    verified_by: Mapped[str] = mapped_column(String(36))
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    release_evidence_sha256: Mapped[str | None] = mapped_column(Text, nullable=True)


class WorkspaceDeletionEvent(Base):
    __tablename__ = "workspace_deletion_events"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    deletion_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspace_deletions.id", ondelete="RESTRICT"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(40))
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
