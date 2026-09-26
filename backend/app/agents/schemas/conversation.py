from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    ordinal: int
    content: Optional[str]
    tool_calls: Optional[list[Any]]
    tool_result: Optional[dict[str, Any]]
    citations: Optional[list[Any]]
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    created_at: datetime


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_id: uuid.UUID
    channel: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime


class SendMessageRequest(BaseModel):
    # Bound direct-API callers as well as the UI. This protects provider cost,
    # prompt size, persistence, and log/trace volume from a single oversized
    # request without preventing normal long-form finance questions.
    content: str = Field(min_length=1, max_length=12_000)
    conversation_id: Optional[uuid.UUID] = None
    channel: str = Field(default="web", min_length=1, max_length=32)
    # Where the user is in the app when this message was sent. The
    # executor injects a short system message so the agent can answer
    # context-aware questions like "what about THIS row?". Format is
    # free-form — the frontend builds it from the active page.
    page_context: Optional[dict[str, Any]] = None

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message content cannot be blank")
        return value

    @field_validator("page_context")
    @classmethod
    def bound_page_context(
        cls,
        value: Optional[dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        if value is None:
            return None
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        if len(encoded.encode("utf-8")) > 20_000:
            raise ValueError("page_context exceeds 20 KB")
        return value
