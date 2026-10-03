import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Awaitable, Optional, cast

from sqlalchemy import desc, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.fx_rate import FxRate
from app.models.user import User
from app.providers.openexchangerates import FxProviderError, OpenExchangeRatesProvider, RateSnapshot

logger = logging.getLogger(__name__)

_provider = OpenExchangeRatesProvider()


class FxRateUnavailableError(RuntimeError):
    """Raised when a cross-currency value cannot be converted truthfully."""

    def __init__(self, from_currency: str, to_currency: str, target_date: Optional[date] = None):
        self.from_currency = from_currency
        self.to_currency = to_currency
        self.target_date = target_date
        super().__init__(
            f"FX rate unavailable for {from_currency} -> {to_currency}"
            + (f" on {target_date.isoformat()}" if target_date else "")
        )


FX_REQUEST_BUDGET_SCRIPT = """
    if redis.call('EXISTS', KEYS[1]) == 1 then return 0 end
    local count = tonumber(redis.call('GET', KEYS[2]) or '0')
    if count >= 24 then return 0 end
    redis.call('SET', KEYS[1], '1', 'EX', 3600)
    redis.call('INCR', KEYS[2])
    redis.call('EXPIRE', KEYS[2], 172800)
    return 1
    """

async def _reserve_provider_request(target: date) -> bool:
    """Shared production budget: <=24 attempts/day and one/date/hour.

    Reserve attempts before HTTP, including failures; Redis outage fails closed.
    Atomic Lua prevents API/worker races. Two daily scheduled calls fit well
    below a 1,000/month plan while leaving room for historical imports.
    """
    from app.core.redis_runtime import create_async_redis_client

    try:
        settings = get_settings()
        # Celery creates a fresh event loop per invocation. Do not reuse the
        # API's async Redis singleton across those closed worker loops.
        async with create_async_redis_client(
            settings.redis_url,
            max_connections=1,
            socket_connect_timeout_seconds=settings.redis_socket_connect_timeout_seconds,
            socket_timeout_seconds=settings.redis_socket_timeout_seconds,
            health_check_interval_seconds=settings.redis_health_check_interval_seconds,
            ssl_ca_file=settings.redis_ssl_ca_file,
            client_name="fincopilot-fx-budget",
        ) as client:
            return await cast(Awaitable[int], client.eval(
                FX_REQUEST_BUDGET_SCRIPT, 2, f"fx:attempt:{target.isoformat()}",
                f"fx:budget:{datetime.now(timezone.utc).date().isoformat()}"
            )) == 1
    except Exception:
        raise FxProviderError("FX request budget unavailable") from None


async def sync_rates(
    session: AsyncSession, target_date: Optional[date] = None
) -> int:
    """Fetch rates from the provider for the given date and upsert into fx_rates.

    Only saves rates for currencies in `supported_currencies`.
    Idempotent — existing rates for the same date are updated.
    Returns the number of rates synced.
    """
    today = datetime.now(timezone.utc).date()
    requested_target = target_date or today
    # Providers cannot return a historical rate for a date that has not
    # happened yet. Treat a future request as a request for today's latest
    # published rate and retain the provider's publication date.
    target = min(requested_target, today)
    if get_settings().is_production and not await _reserve_provider_request(target):
        return 0
    supported = {code.strip().upper() for code in get_settings().supported_currencies.split(",")}

    if target == today:
        rates = await _provider.fetch_latest()
    else:
        rates = await _provider.fetch_historical(target)

    if isinstance(rates, RateSnapshot):
        target = rates.published_date

    if get_settings().is_production and supported - rates.keys():
        raise FxProviderError("FX snapshot does not cover all supported currencies")

    count = 0
    for currency_code, rate in rates.items():
        if currency_code not in supported:
            continue
        stmt = pg_insert(FxRate).values(
            base_currency="USD",
            quote_currency=currency_code,
            date=target,
            rate=rate,
            source=_provider.name,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_fx_rate_base_quote_date",
            set_={"rate": rate, "source": _provider.name},
        )
        await session.execute(stmt)
        count += 1

    await session.commit()
    logger.info("Synced %d FX rates for %s", count, target)
    return count


async def _resolve_rate(
    session: AsyncSession,
    from_currency: str,
    to_currency: str,
    target_date: Optional[date] = None,
    *,
    allow_fetch: bool = True,
) -> Optional[Decimal]:
    """Resolve the true FX rate, or None when no rate can be found.

    Uses cross-rate through USD: rate = usd_to_target / usd_to_source.
    Priority: exact date → on-demand fetch → shared publication date within seven days.
    Returns None (not a fake 1:1) when no rate is available, so callers that
    persist a conversion can honestly leave it NULL instead of storing a wrong
    amount. Pass ``allow_fetch=False`` to skip the on-demand provider call and
    rely only on already-stored rates.
    """
    if from_currency == to_currency:
        return Decimal("1")

    today = datetime.now(timezone.utc).date()
    requested_target = target_date or today
    # A future transaction must use the latest real rate, never query a
    # not-yet-existing historical snapshot. Looking up against today also
    # lets the closest-rate fallback select the last cached business day.
    target = min(requested_target, today)

    # Step 1: Try exact date
    usd_to_source = await _get_exact_date_rate(session, from_currency, target)
    usd_to_target = await _get_exact_date_rate(session, to_currency, target)

    # Step 2: If missing, fetch from provider for exact date
    if allow_fetch and get_settings().fx_sync_mode == "on_demand" and (usd_to_source is None or usd_to_target is None):
        try:
            synced = await sync_rates(session, target)
            if synced > 0:
                logger.info("On-demand sync fetched %d rates for %s", synced, target)
                if usd_to_source is None:
                    usd_to_source = await _get_exact_date_rate(session, from_currency, target)
                if usd_to_target is None:
                    usd_to_target = await _get_exact_date_rate(session, to_currency, target)
        except Exception:
            logger.warning("On-demand FX rate sync failed for %s", target)

    # Never blend legs from different publication dates, or use a future rate.
    if usd_to_source is None or usd_to_target is None:
        currencies = {from_currency, to_currency} - {"USD"}
        common_date = await session.scalar(
            select(FxRate.date)
            .where(
                FxRate.base_currency == "USD",
                FxRate.quote_currency.in_(currencies),
                FxRate.date <= target,
                FxRate.date >= target - timedelta(days=7),
                FxRate.rate > 0,
            )
            .group_by(FxRate.date)
            .having(func.count(func.distinct(FxRate.quote_currency)) == len(currencies))
            .order_by(desc(FxRate.date))
            .limit(1)
        )
        if common_date is None:
            return None
        usd_to_source = await _get_exact_date_rate(session, from_currency, common_date)
        usd_to_target = await _get_exact_date_rate(session, to_currency, common_date)

    if from_currency == "USD":
        usd_to_source = Decimal("1")
    if to_currency == "USD":
        usd_to_target = Decimal("1")

    if usd_to_source is None or usd_to_target is None or not usd_to_source.is_finite() or not usd_to_target.is_finite() or usd_to_source <= 0 or usd_to_target <= 0:
        return None

    return usd_to_target / usd_to_source


async def get_rate(
    session: AsyncSession,
    from_currency: str,
    to_currency: str,
    target_date: Optional[date] = None,
    *,
    allow_fetch: bool = True,
) -> Decimal:
    """Get a truthful FX rate from ``from_currency`` to ``to_currency``.

    Development/test installations can explicitly keep the historical 1:1
    fallback via FX_ALLOW_UNSAFE_1TO1_FALLBACK=true. Production validation
    requires that flag to be false, so an unavailable cross-currency rate
    surfaces as a controlled error rather than a plausible-but-wrong number.
    """
    rate = await _resolve_rate(
        session, from_currency, to_currency, target_date, allow_fetch=allow_fetch
    )
    if rate is not None:
        return rate

    settings = get_settings()
    if settings.fx_allow_unsafe_1to1_fallback:
        logger.warning(
            "No FX rate found for %s -> %s on %s; unsafe development fallback returned 1",
            from_currency,
            to_currency,
            target_date or date.today(),
        )
        return Decimal("1")

    logger.error(
        "No FX rate found for %s -> %s on %s; refusing to fabricate a conversion",
        from_currency,
        to_currency,
        target_date or date.today(),
    )
    raise FxRateUnavailableError(from_currency, to_currency, target_date)


async def _get_exact_date_rate(session: AsyncSession, currency: str, target: date) -> Optional[Decimal]:
    """Get the rate for an exact date."""
    if currency == "USD":
        return Decimal("1")
    result = await session.scalar(
        select(FxRate.rate)
        .where(
            FxRate.base_currency == "USD",
            FxRate.quote_currency == currency,
            FxRate.date == target,
        )
    )
    return result


async def _get_closest_rate(session: AsyncSession, currency: str, target: date) -> Optional[Decimal]:
    """Get the closest available rate to a target date (on or before the target; never look ahead)."""
    if currency == "USD":
        return Decimal("1")
    # Try closest before or on target date
    result = await session.scalar(
        select(FxRate.rate)
        .where(
            FxRate.base_currency == "USD",
            FxRate.quote_currency == currency,
            FxRate.date <= target,
            FxRate.date >= target - timedelta(days=7),
            FxRate.rate > 0,
        )
        .order_by(desc(FxRate.date))
        .limit(1)
    )
    if result is not None:
        return result
    return None


async def convert(
    session: AsyncSession,
    amount: Decimal,
    from_currency: str,
    to_currency: str,
    target_date: Optional[date] = None,
    *,
    allow_fetch: bool = True,
) -> tuple[Decimal, Decimal]:
    """Convert an amount from one currency to another.

    Production refuses to return a fabricated cross-currency value when no
    real rate exists. Development may opt into the legacy fallback explicitly.
    """
    if from_currency == to_currency:
        return amount, Decimal("1")

    rate = await get_rate(
        session, from_currency, to_currency, target_date, allow_fetch=allow_fetch
    )
    converted = amount * rate
    return converted.quantize(Decimal("0.01")), rate


async def stamp_primary_amount(
    session: AsyncSession,
    user_id: uuid.UUID,
    obj,
    amount_field: str = "amount",
    primary_field: str = "amount_primary",
    rate_field: str = "fx_rate_used",
    date_field: str = "date",
    currency_field: str = "currency",
    *,
    allow_fetch: bool = True,
) -> None:
    """Set obj's primary amount and fx_rate_used based on user's primary currency.

    Works for Transaction, RecurringTransaction, etc.

    When the object is in a foreign currency and no real FX rate is available,
    the fields are left untouched instead of persisting a fake 1:1 conversion.
    A brand-new object therefore stays NULL (honest "not converted"), while an
    already-stamped row keeps its current value. It heals on a later pass once a
    real rate for its date lands.
    """
    user = await session.get(User, user_id)
    if not user:
        return

    primary_currency = user.primary_currency
    obj_currency = getattr(obj, currency_field, get_settings().default_currency)
    obj_amount = getattr(obj, amount_field, None)

    if obj_amount is None:
        return

    amount_dec = Decimal(str(obj_amount))

    # Genuine same-currency 1:1 — always safe to persist.
    if obj_currency == primary_currency:
        setattr(obj, primary_field, amount_dec.quantize(Decimal("0.01")))
        if hasattr(obj, rate_field):
            setattr(obj, rate_field, Decimal("1"))
        return

    obj_date = getattr(obj, date_field, None)
    rate = await _resolve_rate(
        session, obj_currency, primary_currency, obj_date, allow_fetch=allow_fetch
    )

    if rate is None:
        return

    setattr(obj, primary_field, (amount_dec * rate).quantize(Decimal("0.01")))
    if hasattr(obj, rate_field):
        setattr(obj, rate_field, rate)
