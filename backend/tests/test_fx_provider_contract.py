"""Exercise real HTTP decoding and fail-closed provider contracts."""
import json
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import httpx
import pytest

from app.providers.openexchangerates import FxProviderError, OpenExchangeRatesProvider, RateSnapshot


async def fetch(payload, status=200, historical=None):
    real_client = httpx.AsyncClient
    def handler(request):
        assert request.headers['authorization'] == 'Token secret-sentinel'
        assert 'app_id' not in request.url.params
        assert 'symbols' not in request.url.params
        return httpx.Response(status, text=payload if isinstance(payload, str) else json.dumps(payload), request=request)
    transport = httpx.MockTransport(handler)
    with patch('app.providers.openexchangerates.get_settings') as settings, patch(
        'app.providers.openexchangerates.httpx.AsyncClient',
        side_effect=lambda **kwargs: real_client(transport=transport, **kwargs),
    ):
        settings.return_value.openexchangerates_app_id = 'secret-sentinel'
        provider = OpenExchangeRatesProvider()
        return await provider.fetch_historical(historical) if historical else await provider.fetch_latest()


def snapshot(**kwargs):
    return {'base': 'USD', 'timestamp': int(datetime.now(timezone.utc).timestamp()),
            'rates': {'USD': 1, 'INR': 83.123456789}, **kwargs}


@pytest.mark.asyncio
async def test_decimal_and_publication_date():
    rates = await fetch(snapshot())
    assert isinstance(rates, RateSnapshot)
    assert rates['INR'] == Decimal('83.123456789')
    assert rates.published_date == datetime.now(timezone.utc).date()


@pytest.mark.asyncio
@pytest.mark.parametrize('rates', [{}, {'INR': 0}, {'INR': -1}, {'INR': True}, {'INR': 'NaN'},
                                  {'INR': float('inf')}, {'USD': 2}, {'inr': 83},
                                  {'INR': 1e10}, {'INR': 1e-11}])
async def test_invalid_rates_rejected(rates):
    with pytest.raises(FxProviderError, match='invalid USD snapshot'):
        await fetch(snapshot(rates=rates))


@pytest.mark.asyncio
@pytest.mark.parametrize('metadata', [{'base': 'EUR'}, {'timestamp': True},
    {'timestamp': 0}, {'timestamp': 99999999999}])
async def test_invalid_metadata_rejected(metadata):
    with pytest.raises(FxProviderError):
        await fetch(snapshot(**metadata))


@pytest.mark.asyncio
async def test_historical_date_must_match():
    with pytest.raises(FxProviderError):
        await fetch(snapshot(), historical=date(2025, 1, 1))


@pytest.mark.asyncio
@pytest.mark.parametrize('status', [301, 401, 429, 500])
async def test_http_errors_do_not_expose_credentials(status):
    with pytest.raises(FxProviderError) as caught:
        await fetch(snapshot(), status=status)
    assert 'secret-sentinel' not in str(caught.value)
    assert caught.value.__suppress_context__


@pytest.mark.asyncio
async def test_http_logs_have_no_app_id(caplog):
    import logging
    caplog.set_level(logging.INFO, logger='httpx')
    await fetch(snapshot())
    assert 'secret-sentinel' not in caplog.text
    assert 'app_id=' not in caplog.text


@pytest.mark.asyncio
async def test_budget_denial_and_redis_failure():
    from unittest.mock import AsyncMock
    from app.services.fx_rate_service import _reserve_provider_request
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.eval.return_value = 0
    with patch('app.core.redis_runtime.create_async_redis_client', return_value=client):
        assert not await _reserve_provider_request(date(2025, 1, 1))
    client.eval.side_effect = RuntimeError('secret-sentinel')
    with patch('app.core.redis_runtime.create_async_redis_client', return_value=client):
        with pytest.raises(FxProviderError) as caught:
            await _reserve_provider_request(date(2025, 1, 1))
    assert 'secret-sentinel' not in str(caught.value)


@pytest.mark.asyncio
async def test_budget_client_closed_after_each_worker_invocation():
    from unittest.mock import AsyncMock
    from app.services.fx_rate_service import _reserve_provider_request
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.eval.return_value = 1
    with patch('app.core.redis_runtime.create_async_redis_client', return_value=client) as factory:
        assert await _reserve_provider_request(date(2025, 1, 1))
        assert await _reserve_provider_request(date(2025, 1, 2))
    assert factory.call_count == 2
    assert client.__aexit__.await_count == 2


@pytest.mark.asyncio
async def test_rate_that_rounds_past_database_precision_is_rejected():
    timestamp = int(datetime.now(timezone.utc).timestamp())
    body = '{"base":"USD","timestamp":' + str(timestamp) + ',"rates":{"INR":9999999999.99999999999}}'
    with pytest.raises(FxProviderError):
        await fetch(body)
