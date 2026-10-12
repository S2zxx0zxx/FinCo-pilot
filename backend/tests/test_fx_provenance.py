"""Production cache provenance cannot be replaced by plausible numeric rates."""
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.models.account import Account
from app.models.fx_rate import FxRate
from app.schemas.spending_plan import SpendingPlanRequest
from app.services import fx_rate_service as fx
from app.services import spending_plan_service as spending

pytestmark = pytest.mark.usefixtures('clean_db')


@pytest.fixture
def production_fx(monkeypatch):
    monkeypatch.setattr(fx._provider, 'name', 'openexchangerates')
    monkeypatch.setattr(fx, 'get_settings', lambda: SimpleNamespace(
        is_production=True, fx_sync_mode='scheduled', fx_allow_unsafe_1to1_fallback=False))


async def rates(session, eur_source, inr_source, published=None, inr_rate='83'):
    published = published or datetime.now(timezone.utc).date()
    session.add_all([
        FxRate(base_currency='USD', quote_currency='EUR', date=published,
               rate=Decimal('0.9'), source=eur_source),
        FxRate(base_currency='USD', quote_currency='INR', date=published,
               rate=Decimal(inr_rate), source=inr_source),
    ])
    await session.commit()


@pytest.mark.parametrize('source', ['manual', 'test', 'unknown'])
async def test_production_exact_and_closest_rates_reject_unapproved_source(session, production_fx, source):
    await rates(session, source, source)
    today = datetime.now(timezone.utc).date()
    assert await fx._get_exact_date_rate(session, 'INR', today) is None
    assert await fx._get_closest_rate(session, 'INR', today) is None
    with pytest.raises(fx.FxRateUnavailableError):
        await fx.get_rate(session, 'EUR', 'INR', allow_fetch=False)


@pytest.mark.parametrize('eur_source,inr_source', [
    ('manual', 'openexchangerates'), ('openexchangerates', 'test'),
])
async def test_same_date_does_not_authorize_mixed_sources(session, production_fx, eur_source, inr_source):
    await rates(session, eur_source, inr_source)
    assert await fx._resolve_rate(session, 'EUR', 'INR', allow_fetch=False) is None


async def test_newer_unapproved_rates_cannot_hide_valid_approved_snapshot(session, production_fx):
    today = datetime.now(timezone.utc).date()
    await rates(session, 'manual', 'manual', today, inr_rate='1000')
    await rates(session, 'openexchangerates', 'openexchangerates', today - timedelta(days=1))
    assert await fx.get_rate(session, 'EUR', 'INR', allow_fetch=False) == Decimal('83') / Decimal('0.9')


@pytest.mark.parametrize('source,accepted', [('test', False), ('manual', False), ('openexchangerates', True)])
async def test_safe_to_spend_uses_same_provenance_gate(session, test_user, test_workspace, production_fx, source, accepted):
    test_user.preferences = {**(test_user.preferences or {}), 'currency_display': 'INR'}
    cash = Account(id=uuid.uuid4(), user_id=test_user.id, workspace_id=test_workspace.id,
                   name='Manual EUR', type='checking', balance=Decimal('0'), currency='EUR')
    session.add(cash)
    await rates(session, source, source)
    today = datetime.now(timezone.utc).date()
    request = SpendingPlanRequest(obligations_reviewed=True, manual_balances={cash.id: {
        'amount': '100', 'currency': 'EUR', 'kind': 'cash', 'as_of': today}})
    plan = await spending.calculate_spending_plan(session, test_workspace.id, test_user.id, request)
    assert (plan.safe_to_spend is not None) == accepted
    if accepted:
        assert plan.cash_balance == Decimal('100') * Decimal('83') / Decimal('0.9')
        assert plan.safe_to_spend == Decimal('9222.22')
    else:
        assert plan.cash_balance is None
        assert any('exchange rate' in message for message in plan.blockers)


async def test_same_currency_remains_exact_without_provider_cache(session, production_fx):
    assert await fx.convert(session, Decimal('123.45'), 'INR', 'INR', allow_fetch=False) == (Decimal('123.45'), Decimal('1'))


async def test_manual_confirmation_uses_utc_day_even_when_host_local_day_differs(session, test_user, test_workspace, monkeypatch):
    utc_now = datetime(2026, 10, 12, 0, 30, tzinfo=timezone.utc)

    class UtcClock(datetime):
        @classmethod
        def now(cls, tz=None):
            assert tz is timezone.utc
            return utc_now

    class LocalDay(date):
        @classmethod
        def today(cls):
            return date(2026, 10, 11)

    monkeypatch.setattr(spending, 'datetime', UtcClock)
    monkeypatch.setattr(spending, 'date', LocalDay)
    cash = Account(id=uuid.uuid4(), user_id=test_user.id, workspace_id=test_workspace.id,
                   name='Current manual cash', type='checking', balance=Decimal('0'), currency=test_user.primary_currency)
    session.add(cash)
    await session.commit()
    request = SpendingPlanRequest(obligations_reviewed=True, manual_balances={cash.id: {
        'amount': '250', 'currency': cash.currency, 'kind': 'cash', 'as_of': utc_now.date()}})
    plan = await spending.calculate_spending_plan(session, test_workspace.id, test_user.id, request)
    assert plan.safe_to_spend == Decimal('250')
