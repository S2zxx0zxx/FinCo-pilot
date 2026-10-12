"""Conservative cash planning. Never treats credit limits or future income as cash.

Read-only: no provider calls or FX ingestion. Missing/stale data blocks the
headline instead of being replaced with synthetic balances or exchange rates.
"""
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_DOWN

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.loan import Loan
from app.schemas.loan import LoanRead
from app.services.loan_service import amortize
from app.models.bank_connection import BankConnection
from app.models.fx_rate import FxRate
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.spending_plan import SpendingPlan, SpendingPlanRequest
from app.services._query_filters import is_not_ignored
from app.services.dashboard_service import _get_open_accounts, get_projected_transactions

ZERO = Decimal(0)
CASH_TYPES = {'checking', 'savings', 'wallet'}


async def calculate_spending_plan(session: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID, request: SpendingPlanRequest) -> SpendingPlan:
    today = date.today()
    through = today + timedelta(days=request.horizon_days - 1)
    user = await session.get(User, user_id)
    if user is None:
        raise ValueError("User not found")
    currency = user.primary_currency
    accounts = await _get_open_accounts(session, workspace_id)
    relevant = {a.id: a for a in accounts if a.type in CASH_TYPES | {'credit_card'}}
    blockers = []
    assumptions = [
        'All amounts use your primary currency. This is an estimate, not a bank spending authorization.',
        'Future income, investment assets and unused credit limits are excluded.',
        'The full current card debt is reserved, even if its due date is beyond this horizon.',
        'Pending debits are reserved conservatively; a provider balance may already include them.',
        'Emergency savings, goal contributions and obligations missing from your ledger must be entered separately.',
        'Paired transfers between included cash accounts are excluded. Card repayments remain reserved conservatively.',
    ]
    if not any(a.type in CASH_TYPES for a in accounts):
        blockers.append('Add and reconcile at least one cash account.')
    if not request.obligations_reviewed:
        blockers.append('Review balances, scheduled bills, loan repayments and other obligations before using this estimate.')
    if any(a.type not in CASH_TYPES | {'credit_card', 'investment'} for a in accounts):
        blockers.append('An unsupported account type may contain debt; reconcile it before calculating.')

    # Only recent cached USD cross-rates are accepted, with an explicit age cap.
    snapshots: dict[date, dict[str, Decimal]] = {}
    fx = (await session.scalars(select(FxRate).where(
        FxRate.base_currency == 'USD', FxRate.date <= today,
        FxRate.date >= today - timedelta(days=7),
    ).order_by(FxRate.date.desc()))).all()
    for row in fx:
        snapshot = snapshots.setdefault(row.date, {"USD": Decimal(1)})
        if row.quote_currency != "USD":
            snapshot[row.quote_currency] = row.rate

    def convert(amount, source):
        amount = Decimal(str(amount))
        if source == currency:
            return amount
        rates = next((snapshot for snapshot in snapshots.values()
                      if source in snapshot and currency in snapshot
                      and snapshot[source].is_finite() and snapshot[currency].is_finite()
                      and snapshot[source] > 0 and snapshot[currency] > 0), None)
        if rates is None:
            blockers.append(f'A recent exchange rate for {source}/{currency} is unavailable.')
            return ZERO
        return amount * rates[currency] / rates[source]

    cash = debt = outflows = ZERO
    manual_ids = [a.id for a in relevant.values() if not a.connection_id]
    # A ledger's net flow cannot prove its opening or present-day balance.
    # Manual confirmations remain read-only, explicit and workspace-bound.
    for aid, confirmation in request.manual_balances.items():
        account = relevant.get(aid)
        expected_kind = 'card_debt' if account and account.type == 'credit_card' else 'cash'
        if (account is None or account.connection_id or confirmation.kind != expected_kind
                or confirmation.currency != account.currency or confirmation.as_of != today):
            raise HTTPException(400, 'Manual balance confirmations must match current manual accounts, currencies, types and date in this workspace.')
    cash_unknown = debt_unknown = False
    connection_ids = {a.connection_id for a in relevant.values() if a.connection_id}
    connections = (await session.scalars(select(BankConnection).where(BankConnection.id.in_(connection_ids)))).all() if connection_ids else []
    for conn in connections:
        # Legacy Enable Banking rows can still label liabilities as checking until
        # a complete resync. SimpleFIN exposes no account type at all.
        # A fresh balance is not evidence that the balance is spendable cash.
        if conn.provider in {'enable_banking', 'simplefin'}:
            blockers.append(
                f'Safe-to-spend is unavailable for {conn.display_name or conn.institution_name}: '
                'this bank connection does not yet reliably distinguish cash from loan accounts.'
            )
        refresh = conn.last_provider_refresh_at
        refresh = refresh.replace(tzinfo=timezone.utc) if refresh and refresh.tzinfo is None else refresh
        if conn.status != 'active' or refresh is None or datetime.now(timezone.utc) - refresh > timedelta(hours=24):
            blockers.append(f'Confirm a fresh bank refresh for {conn.display_name or conn.institution_name}; a cached ingestion alone is insufficient.')
    if manual_ids:
        assumptions.append('Manual amounts are entered and confirmed by you for this calculation; they are not bank-verified and do not change your ledger.')
    for account in relevant.values():
        is_debt = account.type == 'credit_card'
        confirmation = request.manual_balances.get(account.id)
        if not account.connection_id and confirmation is None:
            blockers.append(f'Confirm today’s {"outstanding card debt" if is_debt else "cash balance"} for {account.name}; transaction history does not confirm today’s balance.')
            debt_unknown = debt_unknown or is_debt
            cash_unknown = cash_unknown or not is_debt
            continue
        if account.connection_id:
            value = account.balance
        else:
            assert confirmation is not None
            value = confirmation.amount
        previous_blockers = len(blockers)
        amount = convert(value, account.currency)
        if len(blockers) != previous_blockers:
            debt_unknown = debt_unknown or is_debt
            cash_unknown = cash_unknown or not is_debt
        if is_debt:
            debt += max(ZERO, amount)
        else:
            cash += amount

    if relevant:
        pending = (await session.scalars(select(Transaction).where(
            Transaction.account_id.in_(relevant), Transaction.date <= through,
            or_(Transaction.status == 'pending', Transaction.date > today),
            Transaction.type == 'debit', Transaction.source != 'opening_balance', is_not_ignored(),
        ))).all()
        pair_ids = {t.transfer_pair_id for t in pending if t.transfer_pair_id}
        cash_ids = {a.id for a in relevant.values() if a.type in CASH_TYPES}
        internal_pairs = set()
        if pair_ids:
            internal_pairs = set((await session.scalars(select(Transaction.transfer_pair_id).where(
                Transaction.transfer_pair_id.in_(pair_ids), Transaction.account_id.in_(cash_ids),
                Transaction.type == 'credit', Transaction.date <= through, is_not_ignored(),
                or_(Transaction.status == 'pending', Transaction.date > today),
            ))).all())
        for tx in pending:
            if tx.account_id in cash_ids and tx.transfer_pair_id in internal_pairs:
                continue
            outflows += convert(abs(tx.amount), tx.currency)
        # The shared projector suppresses already-materialized occurrences.
        projected = await get_projected_transactions(session, workspace_id, user_id, from_date=today, to_date=through, allow_fx_fetch=False)
        for tx in projected:
            if tx.type == 'debit' and (tx.account_id is None or uuid.UUID(tx.account_id) in relevant):
                outflows += convert(abs(tx.amount), tx.currency)

    loan_reserve = ZERO
    loans = (await session.scalars(select(Loan).where(
        Loan.workspace_id == workspace_id, Loan.archived == False,
    ))).all()
    for loan in loans:
        due = sum((item.payment for item in amortize(LoanRead.model_validate(loan))
                   if not item.reported_paid and item.due_date <= through), start=ZERO)
        if due:
            loan_reserve += convert(due, loan.currency)
    if loans:
        assumptions.append(
            'Loan reserves include every self-reported unpaid installment due through the horizon, '
            'including overdue installments. Verify paid counts against lender statements. '
            'These estimates exclude fees, floating rates and partial or early principal repayments. '
            'Loan dues also entered as recurring or pending expenses are conservatively reserved twice; '
            'do not add the same loan again under other obligations.'
        )

    available = cash - debt - outflows - loan_reserve - request.emergency_buffer - request.goal_reserve - request.other_obligations
    blockers = list(dict.fromkeys(blockers))
    # Round the usable amount down, never up. Whole decimal strings in JSON.
    usable = max(ZERO, available).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
    return SpendingPlan(
        currency=currency, as_of=today, through=through,
        status='needs_review' if blockers else 'estimated',
        cash_balance=None if cash_unknown else cash, card_debt_reserve=None if debt_unknown else debt, upcoming_outflows=outflows,
        loan_due_reserve=loan_reserve,
        emergency_buffer=request.emergency_buffer, goal_reserve=request.goal_reserve,
        other_obligations=request.other_obligations,
        safe_to_spend=None if blockers else usable,
        daily_allowance=None if blockers else (usable / request.horizon_days).quantize(Decimal('0.01'), rounding=ROUND_DOWN),
        shortfall=None if blockers else max(ZERO, -available), blockers=blockers, assumptions=assumptions,
    )
