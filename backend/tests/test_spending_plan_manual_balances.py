"""Account-scoped current amounts, not an invented balance from partial history."""
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, select

from app.models.account import Account
from app.models.transaction import Transaction
from app.schemas.spending_plan import SpendingPlanRequest
from app.services.spending_plan_service import calculate_spending_plan


@pytest.fixture
async def partial_ledger(session, test_user, test_workspace):
    row = Account(id=uuid.uuid4(), user_id=test_user.id, workspace_id=test_workspace.id,
                  name='Partial history', type='checking', balance=Decimal(0), currency=test_user.primary_currency)
    session.add(row)
    await session.flush()
    session.add(Transaction(user_id=test_user.id, workspace_id=test_workspace.id, account_id=row.id,
                            description='Imported receipt', amount=Decimal('10000'), currency=row.currency,
                            type='credit', source='manual', status='posted', date=date.today(), effective_date=date.today()))
    await session.commit()
    return row


def confirmed(row, amount, **updates):
    item = {'amount': amount, 'currency': row.currency, 'kind': 'cash', 'as_of': date.today()}
    item.update(updates)
    return {row.id: item}


async def calculate(session, user, workspace, balances=None):
    return await calculate_spending_plan(session, workspace.id, user.id,
        SpendingPlanRequest(obligations_reviewed=True, manual_balances=balances or {}))


async def test_partial_ledger_is_unknown_even_after_review(session, test_user, test_workspace, partial_ledger):
    plan = await calculate(session, test_user, test_workspace)
    assert plan.cash_balance is None
    assert plan.safe_to_spend is None
    assert plan.daily_allowance is None
    assert plan.shortfall is None
    assert any('transaction history' in item for item in plan.blockers)


@pytest.mark.parametrize('amount,expected,shortfall', [('0', 0, 0), ('250.25', Decimal('250.25'), 0), ('-100', 0, 100)])
async def test_explicit_amount_ignores_partial_flow_without_writing(session, test_user, test_workspace, partial_ledger, amount, expected, shortfall):
    before = await session.scalar(select(func.count()).select_from(Transaction))
    plan = await calculate(session, test_user, test_workspace, confirmed(partial_ledger, amount))
    assert plan.safe_to_spend == expected
    assert plan.shortfall == shortfall
    assert plan.cash_balance == Decimal(amount)
    assert partial_ledger.balance == 0
    assert await session.scalar(select(func.count()).select_from(Transaction)) == before
    assert any('not bank-verified' in item for item in plan.assumptions)


@pytest.mark.parametrize('updates', [{'currency': 'USD'}, {'kind': 'card_debt'}, {'as_of': date.today()-timedelta(days=1)}, {'as_of': date.today()+timedelta(days=1)}])
async def test_wrong_currency_type_or_date_is_rejected(session, test_user, test_workspace, partial_ledger, updates):
    if updates.get('currency') == partial_ledger.currency:
        updates = {'currency': 'EUR'}
    with pytest.raises(HTTPException) as error:
        await calculate(session, test_user, test_workspace, confirmed(partial_ledger, '250', **updates))
    assert error.value.status_code == 400


async def test_actual_other_workspace_account_is_rejected(session, test_user, test_workspace, partial_ledger):
    from app.models.workspace import Workspace
    other = Workspace(id=uuid.uuid4(), name='Other', kind='personal', created_by_user_id=test_user.id,
                      billing_owner_user_id=test_user.id, default_currency=partial_ledger.currency)
    session.add(other)
    await session.flush()
    foreign = Account(id=uuid.uuid4(), user_id=test_user.id, workspace_id=other.id, name='Foreign',
                      type='checking', balance=Decimal('250'), currency=partial_ledger.currency)
    session.add(foreign)
    await session.flush()
    with pytest.raises(HTTPException) as error:
        await calculate(session, test_user, test_workspace, confirmed(foreign, '250'))
    assert error.value.status_code == 400


async def test_provider_amount_cannot_be_overridden(session, test_user, test_workspace, test_account):
    assert test_account.connection_id is not None
    with pytest.raises(HTTPException) as error:
        await calculate(session, test_user, test_workspace, confirmed(test_account, '100000'))
    assert error.value.status_code == 400


async def test_unknown_cash_and_debt_are_not_zero_totals(session, test_user, test_workspace, partial_ledger):
    session.add_all([Account(user_id=test_user.id, workspace_id=test_workspace.id, name='Unknown savings',
                            type='savings', balance=Decimal(0), currency=partial_ledger.currency),
                     Account(user_id=test_user.id, workspace_id=test_workspace.id, name='Unknown card',
                             type='credit_card', balance=Decimal(0), currency=partial_ledger.currency)])
    await session.flush()
    plan = await calculate(session, test_user, test_workspace, confirmed(partial_ledger, '250'))
    assert plan.cash_balance is None
    assert plan.card_debt_reserve is None
    assert plan.safe_to_spend is None


async def test_card_debt_is_reserved_not_unused_credit_limit(session, test_user, test_workspace, partial_ledger):
    card = Account(id=uuid.uuid4(), user_id=test_user.id, workspace_id=test_workspace.id, name='Card',
                   type='credit_card', balance=Decimal(0), credit_limit=Decimal('100000'), currency=partial_ledger.currency)
    session.add(card)
    await session.flush()
    plan = await calculate(session, test_user, test_workspace,
                           confirmed(partial_ledger, '250') | confirmed(card, '200', kind='card_debt'))
    assert plan.card_debt_reserve == 200
    assert plan.safe_to_spend == 50


@pytest.mark.parametrize('amount', ['NaN', 'Infinity', '-Infinity', '1.001', '1000000000000'])
def test_invalid_amounts_rejected(amount):
    with pytest.raises(ValidationError):
        SpendingPlanRequest(manual_balances={uuid.uuid4(): {'amount': amount, 'currency': 'INR', 'kind': 'cash', 'as_of': date.today()}})


@pytest.mark.parametrize('updates', [{'amount': '-1', 'kind': 'card_debt'}, {'bank_verified': True}])
def test_negative_debt_and_invented_bank_proof_are_rejected(updates):
    item = {'amount': '100', 'currency': 'INR', 'kind': 'cash', 'as_of': date.today()}
    item.update(updates)
    with pytest.raises(ValidationError):
        SpendingPlanRequest(manual_balances={uuid.uuid4(): item})
