"""Reject oversized storage uploads before billing, decoding or provider writes."""
import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, UploadFile

from app.api import attachments, invoice_attachments, invoices
from app.core.config import get_settings
from app.core.workspace_context import WorkspaceContext
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["transaction", "invoice", "logo"])
async def test_storage_upload_reads_only_existing_budget(kind, monkeypatch):
    monkeypatch.setattr(get_settings(), "storage_max_file_size_mb", 1)
    budget = 1024 * 1024
    file = AsyncMock(spec=UploadFile)
    file.filename = "private.png"
    file.content_type = "image/png"
    file.read.return_value = b"x" * (budget + 1)
    uid, wid = uuid.uuid4(), uuid.uuid4()
    ctx = WorkspaceContext(workspace=Workspace(id=wid),
        member=WorkspaceMember(workspace_id=wid, user_id=uid, role="owner"), user=User(id=uid))
    session = AsyncMock()
    bill = AsyncMock()
    store = AsyncMock()
    monkeypatch.setattr(attachments, "enforce_limit", bill)
    monkeypatch.setattr(invoice_attachments, "enforce_limit", bill)
    monkeypatch.setattr(attachments.attachment_service, "upload_attachment", store)
    monkeypatch.setattr(invoice_attachments.invoice_attachment_service, "upload", store)
    monkeypatch.setattr(invoices.invoice_logo_service, "store", store)
    monkeypatch.setattr(invoices.invoice_service, "get_settings", AsyncMock())
    with pytest.raises(HTTPException) as error:
        if kind == "transaction":
            await attachments.upload_attachment(uuid.uuid4(), file, ctx, session)
        elif kind == "invoice":
            await invoice_attachments.upload_attachment(uuid.uuid4(), file, ctx=ctx, session=session)
        else:
            await invoices.upload_logo(file, ctx, session)
    assert error.value.status_code == 400  # retain storage API's existing rejection contract
    assert "too large" in error.value.detail.lower()
    file.read.assert_awaited_once_with(budget + 1)
    bill.assert_not_awaited()
    store.assert_not_awaited()
