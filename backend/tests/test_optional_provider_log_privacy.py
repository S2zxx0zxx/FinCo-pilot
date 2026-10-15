"""Optional market/bank failures retain graceful fallback without raw payload logs."""
import logging
import uuid
from unittest.mock import AsyncMock

import pytest

from app.api import assets
from app.models.account import Account
from app.models.bank_connection import BankConnection
from app.services import connection_service


@pytest.mark.asyncio
@pytest.mark.parametrize("surface", ["holdings", "bills", "market"])
async def test_optional_provider_failures_do_not_log_private_payloads(surface, monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    marker = "PRIVATE-provider-body-https://user:secret@example.invalid/account/123"
    provider = AsyncMock()
    for name in ("get_holdings", "get_bills", "search"):
        getattr(provider, name).side_effect = RuntimeError(marker)
    session = AsyncMock()
    uid = uuid.uuid4()
    if surface == "holdings":
        monkeypatch.setattr(connection_service, "get_provider", lambda name: provider)
        result = await connection_service._sync_holdings(
            session, uid, BankConnection(id=uuid.uuid4(), provider="synthetic"), {},
        )
        assert result is None
    elif surface == "bills":
        result = await connection_service._sync_credit_card_bills(
            session, uid, Account(id=uuid.uuid4(), type="credit_card"), provider, {},
        )
        assert result == {}
    else:
        monkeypatch.setattr(assets, "get_market_price_provider", lambda: provider)
        assert await assets.market_search(q="PRIVATE-financial-query", limit=15) == []
        assert "PRIVATE-financial-query" not in caplog.text
    assert marker not in caplog.text
    assert not any(record.exc_info for record in caplog.records)
    session.execute.assert_not_awaited()
