"""Validated USD snapshots; upstream errors never expose the credential URL."""
import json
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

import httpx

from app.core.config import get_settings
from app.providers.base import FxRateProvider

BASE_URL = "https://openexchangerates.org/api"


class RateSnapshot(dict[str, Decimal]):
    """A USD snapshot carrying the provider publication date."""

    def __init__(self, rates: dict[str, Decimal], published_date: date):
        super().__init__(rates)
        self.published_date = published_date


class FxProviderError(ValueError):
    """A safe, credential-free provider failure."""


class OpenExchangeRatesProvider(FxRateProvider):
    @property
    def name(self) -> str:
        return "openexchangerates"

    async def _fetch(self, target_date: date | None) -> dict[str, Decimal]:
        settings = get_settings()
        app_id = settings.openexchangerates_app_id.strip()
        if not app_id:
            raise FxProviderError("openexchangerates_app_id not configured")
        endpoint = "latest.json" if target_date is None else f"historical/{target_date.isoformat()}.json"
        # Historical symbols availability differs by plan. Fetch the full snapshot
        # and filter locally, avoiding a paid-plan parameter on the free plan.
        headers = {"Authorization": f"Token {app_id}"}
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
                response = await client.get(f"{BASE_URL}/{endpoint}", headers=headers)
                response.raise_for_status()
                data = json.loads(response.text, parse_float=Decimal)
        except (httpx.HTTPError, ValueError):
            raise FxProviderError("FX provider request failed") from None
        try:
            if not isinstance(data, dict) or data.get("base") != "USD":
                raise ValueError
            timestamp = data.get("timestamp")
            if isinstance(timestamp, bool) or not isinstance(timestamp, int):
                raise ValueError
            published = datetime.fromtimestamp(timestamp, timezone.utc)
            now = datetime.now(timezone.utc)
            if published > now or (target_date is not None and published.date() != target_date):
                raise ValueError
            if target_date is None and (now - published).total_seconds() > 86400:
                raise ValueError
            raw_rates = data.get("rates")
            if not isinstance(raw_rates, dict) or not raw_rates:
                raise ValueError
            rates = {}
            for code, value in raw_rates.items():
                if not isinstance(code, str) or len(code) != 3 or not code.isascii() or not code.isalpha() or code != code.upper():
                    raise ValueError
                if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
                    raise ValueError
                rate = Decimal(value)
                # Match Numeric(20,10); reject values that round to zero.
                if not rate.is_finite() or rate < Decimal("0.0000000001") or rate >= Decimal("10000000000"):
                    raise ValueError
                if code == "USD" and rate != 1:
                    raise ValueError
                rates[code] = rate
            return RateSnapshot(rates, published.date())
        except (ValueError, InvalidOperation, OverflowError, OSError):
            raise FxProviderError("FX provider returned an invalid USD snapshot") from None

    async def fetch_latest(self) -> dict[str, Decimal]:
        return await self._fetch(None)

    async def fetch_historical(self, target_date: date) -> dict[str, Decimal]:
        return await self._fetch(target_date)
