from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch
import uuid

import pytest

from app.models.account import Account
from app.models.transaction import Transaction
from app.schemas.dashboard import ProjectedTransaction
from app.schemas.spending_plan import SpendingPlanRequest
from app.services.spending_plan_service import calculate_spending_plan


async def account(session, user, workspace, kind='checking', currency=None):
    row = Account(id=uuid.uuid4(), user_id=user.id, workspace_id=workspace.id, name=kind, type=kind, currency=currency or user.primary_currency, balance=Decimal(0))
    session.add(row)
    await session.flush()
    return row


async def transaction(session, user, workspace, account, amount, kind='debit', days=0, status='posted', pair=None):
    row = Transaction(id=uuid.uuid4(), user_id=user.id, workspace_id=workspace.id, account_id=account.id, description='Plan test', amount=Decimal(amount), currency=account.currency, type=kind, date=date.today()+timedelta(days=days), effective_date=date.today()+timedelta(days=days), source='manual', status=status, transfer_pair_id=pair)
    session.add(row)
    await session.flush()
    return row


@pytest.mark.asyncio
async def test_real_ledger_reserves_debt_bills_buffers_and_excludes_future_income(session, test_user, test_workspace):
    cash = await account(session, test_user, test_workspace)
    card = await account(session, test_user, test_workspace, 'credit_card')
    await transaction(session, test_user, test_workspace, cash, '10000', 'credit')
    await transaction(session, test_user, test_workspace, card, '2000')
    await transaction(session, test_user, test_workspace, cash, '1000', days=2)
    await transaction(session, test_user, test_workspace, cash, '50000', 'credit', days=1)
    await session.commit()
    plan = await calculate_spending_plan(session, test_workspace.id, test_user.id, SpendingPlanRequest(obligations_reviewed=True, emergency_buffer=Decimal('3000'), goal_reserve=Decimal('500'), other_obligations=Decimal('500')))
    assert plan.status == 'estimated'
    assert plan.cash_balance == 10000
    assert plan.card_debt_reserve == 2000
    assert plan.upcoming_outflows == 1000
    assert plan.safe_to_spend == 3000
    assert plan.daily_allowance == 100


@pytest.mark.asyncio
async def test_missing_fx_and_unreviewed_obligations_never_show_spendable_amount(session, test_user, test_workspace):
    cash = await account(session, test_user, test_workspace, currency='ZZZ')
    await transaction(session, test_user, test_workspace, cash, '10000', 'credit')
    plan = await calculate_spending_plan(session, test_workspace.id, test_user.id, SpendingPlanRequest())
    assert plan.safe_to_spend is None
    assert any('exchange rate' in message for message in plan.blockers)
    assert any('Review balances' in message for message in plan.blockers)


@pytest.mark.asyncio
async def test_future_internal_transfers_not_expenses_but_settled_incoming_is_reserved(session, test_user, test_workspace):
    cash = await account(session, test_user, test_workspace)
    savings = await account(session, test_user, test_workspace, 'savings')
    await transaction(session, test_user, test_workspace, cash, '1000', 'credit')
    pair = uuid.uuid4()
    await transaction(session, test_user, test_workspace, cash, '200', days=1, pair=pair)
    await transaction(session, test_user, test_workspace, savings, '200', 'credit', days=1, pair=pair)
    settled_pair = uuid.uuid4()
    await transaction(session, test_user, test_workspace, cash, '100', days=1, pair=settled_pair)
    await transaction(session, test_user, test_workspace, savings, '100', 'credit', pair=settled_pair)
    plan = await calculate_spending_plan(session, test_workspace.id, test_user.id, SpendingPlanRequest(obligations_reviewed=True))
    assert plan.cash_balance == 1100
    assert plan.upcoming_outflows == 100
    assert plan.safe_to_spend == 1000


@pytest.mark.asyncio
async def test_projected_recurring_and_shortfall(session, test_user, test_workspace):
    cash = await account(session, test_user, test_workspace)
    await transaction(session, test_user, test_workspace, cash, '100', 'credit')
    projected = ProjectedTransaction(recurring_id=str(uuid.uuid4()), account_id=str(cash.id), description='Rent', amount=300, currency=cash.currency, type='debit', date=date.today().isoformat(), category_id=None, category_name=None, category_icon=None)
    with patch('app.services.spending_plan_service.get_projected_transactions', return_value=[projected]):
        plan = await calculate_spending_plan(session, test_workspace.id, test_user.id, SpendingPlanRequest(obligations_reviewed=True))
    assert plan.safe_to_spend == 0
    assert plan.shortfall == 200


@pytest.mark.asyncio
async def test_stale_connected_balance_blocks_headline(session, test_user, test_workspace, test_account):
    plan = await calculate_spending_plan(session, test_workspace.id, test_user.id, SpendingPlanRequest(obligations_reviewed=True))
    assert plan.safe_to_spend is None
    assert any('fresh bank refresh' in message for message in plan.blockers)


@pytest.mark.asyncio
async def test_endpoint_input_validation_and_auth(client, auth_headers):
    assert (await client.post('/api/dashboard/spending-plan', json={})).status_code == 401
    assert (await client.post('/api/dashboard/spending-plan', headers=auth_headers, json={'emergency_buffer': '-1'})).status_code == 422
    assert (await client.post('/api/dashboard/spending-plan', headers=auth_headers, json={'horizon_days': 365})).status_code == 422
    assert (await client.post('/api/dashboard/spending-plan', headers=auth_headers, json={})).status_code == 200
