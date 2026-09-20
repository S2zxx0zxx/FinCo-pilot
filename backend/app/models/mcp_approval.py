"""One-time, short-lived human approvals for exact external MCP mutations."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MCPApproval(Base):
    __tablename__ = 'mcp_approvals'
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('external_mcp_tokens.id', ondelete='CASCADE'), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('workspaces.id', ondelete='CASCADE'), index=True)
    tool_name: Mapped[str] = mapped_column(String(120))
    arguments: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default='pending')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
