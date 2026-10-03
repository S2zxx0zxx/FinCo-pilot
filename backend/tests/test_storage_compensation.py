from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select

from app.models.transaction_attachment import TransactionAttachment
from app.services.storage_compensation import compensate_upload


@pytest.mark.asyncio
@pytest.mark.parametrize("referenced", [True, False])
async def test_failed_upload_deletes_only_proven_unreferenced_bytes(referenced):
    session = AsyncMock()
    result = MagicMock()
    result.first.return_value = ("existing-row",) if referenced else None
    session.execute.return_value = result
    storage = AsyncMock()
    await compensate_upload(session, storage, "new-upload", select(TransactionAttachment.id))
    session.rollback.assert_awaited_once()
    if referenced:
        storage.delete.assert_not_awaited()
    else:
        storage.delete.assert_awaited_once_with("new-upload")


@pytest.mark.asyncio
async def test_unknown_database_outcome_preserves_bytes_and_sanitizes_log(caplog):
    session = AsyncMock()
    session.execute.side_effect = RuntimeError("secret-that-must-not-be-logged")
    storage = AsyncMock()
    await compensate_upload(session, storage, "private-object-key", select(TransactionAttachment.id))
    storage.delete.assert_not_awaited()
    assert "compensation deferred" in caplog.text
    assert "secret-that-must-not-be-logged" not in caplog.text
    assert "private-object-key" not in caplog.text
