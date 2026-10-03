import asyncio
import logging
from decimal import Decimal

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.worker import celery_app
from app.core.config import get_settings
from app.core.database_runtime import create_database_engine
from app.models.transaction import Transaction
from app.models.recurring_transaction import RecurringTransaction
from app.models.asset import Asset
from app.models.user import User

logger = logging.getLogger(__name__)


def _make_session_maker():
    settings = get_settings()
    engine = create_database_engine(settings, short_lived=True)
    return engine, async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _backfill_primary_amounts() -> dict:
    """Resume truthful conversions without replacing unresolved existing values."""
    from datetime import datetime, timezone
    from app.services.fx_rate_service import sync_rates, _resolve_rate

    engine, session_maker = _make_session_maker()
    stats = {"transactions": 0, "recurring": 0, "assets": 0, "rates_synced": 0}
    try:
        async with session_maker() as session:
            users = {u.id: u.primary_currency for u in
                     (await session.execute(select(User))).scalars().all()}
            settings = get_settings()
            transactions = (await session.execute(select(Transaction).where(or_(
                Transaction.amount_primary.is_(None), Transaction.fx_rate_used == 1,
            )))).scalars().all()
            recurring = (await session.execute(select(RecurringTransaction).where(or_(
                RecurringTransaction.amount_primary.is_(None), RecurringTransaction.fx_rate_used == 1,
            )))).scalars().all()
            assets = (await session.execute(select(Asset).where(
                Asset.purchase_price.isnot(None), Asset.purchase_price_primary.is_(None),
            ))).scalars().all()
            # Each entry retains its own denomination/date and destination field.
            candidates = []
            for row in transactions:
                primary = users.get(row.user_id, settings.default_currency)
                if row.currency != primary:
                    candidates.append((row, "transactions", "amount", "amount_primary", row.date, primary))
            for row in recurring:
                primary = users.get(row.user_id, settings.default_currency)
                if row.currency != primary:
                    candidates.append((row, "recurring", "amount", "amount_primary", row.next_occurrence, primary))
            for row in assets:
                candidates.append((row, "assets", "purchase_price", "purchase_price_primary", row.purchase_date,
                                   users.get(row.user_id, settings.default_currency)))

            # Fetch only dates whose needed pairs cannot already resolve. This
            # includes recurring/assets-only imports, not just transactions.
            today = datetime.now(timezone.utc).date()
            missing_dates = set()
            for row, _, _, _, target, primary in candidates:
                if await _resolve_rate(session, row.currency, primary, target, allow_fetch=False) is None:
                    missing_dates.add(min(target or today, today))
            for target in sorted(missing_dates):
                try:
                    stats["rates_synced"] += await sync_rates(session, target)
                except Exception:
                    logger.warning("Failed to sync historical FX for %s", target)

            for row, group, amount_field, primary_field, target, primary in candidates:
                rate = await _resolve_rate(session, row.currency, primary, target, allow_fetch=False)
                if rate is None:
                    continue
                amount = getattr(row, amount_field)
                if amount is None:
                    continue
                converted = (Decimal(str(amount)) * rate).quantize(Decimal("0.01"))
                before = (getattr(row, primary_field), getattr(row, "fx_rate_used", None))
                setattr(row, primary_field, converted)
                if hasattr(row, "fx_rate_used"):
                    row.fx_rate_used = rate
                if (getattr(row, primary_field), getattr(row, "fx_rate_used", None)) != before:
                    stats[group] += 1
            await session.commit()
        return stats
    finally:
        await engine.dispose()


@celery_app.task(name="app.tasks.fx_backfill_tasks.backfill_primary_amounts")
def backfill_primary_amounts() -> dict:
    """Celery task: one-time backfill of amount_primary for all existing records."""
    stats = asyncio.run(_backfill_primary_amounts())
    logger.info("Backfill complete: %s", stats)
    return stats
