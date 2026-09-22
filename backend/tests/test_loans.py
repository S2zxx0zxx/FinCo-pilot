import io
import json
import uuid
import zipfile
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.account import Account
from app.models.loan import Loan
from app.models.transaction import Transaction
from app.schemas.loan import LoanCreate
from app.schemas.spending_plan import SpendingPlanRequest
from app.services.loan_service import amortize
from app.services.spending_plan_service import calculate_spending_plan


def payload(**overrides):
    return {
        "name": "Home loan", "principal": "1200.00", "annual_rate": "0",
        "term_months": 12, "first_due_date": "2024-01-31", "currency": "INR",
        "paid_installments": 0, **overrides,
    }


def test_month_end_leap_year_zero_rate_and_exact_principal():
    schedule = amortize(LoanCreate(**payload()))
    assert [x.due_date for x in schedule[:3]] == [date(2024, 1, 31), date(2024, 2, 29), date(2024, 3, 31)]
    assert all(x.payment == Decimal("100") and x.interest == 0 for x in schedule)
    assert sum(x.principal for x in schedule) == Decimal("1200")
    assert schedule[-1].remaining_principal == 0


def test_non_month_end_anchor_recovers_after_february_and_final_rounding():
    schedule = amortize(LoanCreate(**payload(principal="100000", annual_rate="12", first_due_date="2025-01-30")))
    assert [x.due_date.day for x in schedule[:3]] == [30, 28, 30]
    assert schedule[0].payment == Decimal("8884.88")
    assert schedule[0].interest == Decimal("1000")
    assert sum(x.principal for x in schedule) == Decimal("100000")
    assert schedule[-1].remaining_principal == 0
    assert all(x.payment == x.principal + x.interest for x in schedule)


@pytest.mark.parametrize("principal,rate,months", [
    ("1", "0", 600), ("1", "60", 600), ("999999999999", "60", 600),
    ("12345.67", "0.0001", 360), ("1.01", "12", 1),
])
def test_extreme_contracts_reconcile(principal, rate, months):
    data = LoanCreate(**payload(principal=principal, annual_rate=rate, term_months=months))
    schedule = amortize(data)
    assert len(schedule) == months
    assert sum(x.principal for x in schedule) == Decimal(principal)
    assert schedule[-1].remaining_principal == 0
    assert all(x.principal >= 0 and x.interest >= 0 and x.remaining_principal >= 0 for x in schedule)


@pytest.mark.parametrize("overrides", [
    {"name": " "}, {"principal": "NaN"}, {"principal": "-1"}, {"principal": "1.001"},
    {"annual_rate": "Infinity"}, {"annual_rate": "-1"}, {"annual_rate": "61"},
    {"term_months": 0}, {"term_months": 601}, {"paid_installments": 13},
    {"currency": "inr"}, {"currency": "JPY"}, {"first_due_date": "1999-12-31"}, {"surprise": True},
])
def test_invalid_contract_is_rejected(overrides):
    with pytest.raises(ValidationError):
        LoanCreate(**payload(**overrides))


async def test_crud_auth_scope_conflict_and_backup(client, auth_headers, viewer_auth_headers):
    assert (await client.get("/api/loans")).status_code == 401
    assert (await client.post("/api/loans", headers=viewer_auth_headers, json=payload())).status_code == 403
    response = await client.post("/api/loans", headers=auth_headers, json=payload())
    assert response.status_code == 201, response.text
    row = response.json()
    loan_id = row["id"]
    assert row["version"] == 1
    assert len((await client.get("/api/loans", headers=auth_headers)).json()) == 1
    detail = (await client.get(f"/api/loans/{loan_id}", headers=viewer_auth_headers)).json()
    assert detail["remaining_principal"] == "1200.00"
    assert len(detail["schedule"]) == 12
    assert (await client.get(f"/api/loans/{uuid.uuid4()}", headers=auth_headers)).status_code == 404
    patch = {"version": 1, "paid_installments": 2, "archived": False}
    assert (await client.patch(f"/api/loans/{loan_id}", headers=viewer_auth_headers, json=patch)).status_code == 403
    assert (await client.patch(f"/api/loans/{loan_id}", headers=auth_headers, json={**patch, "paid_installments": 13})).status_code == 422
    changed = await client.patch(f"/api/loans/{loan_id}", headers=auth_headers, json=patch)
    assert changed.status_code == 200, changed.text
    assert changed.json()["version"] == 2
    assert (await client.patch(f"/api/loans/{loan_id}", headers=auth_headers, json=patch)).status_code == 409
    detail = (await client.get(f"/api/loans/{loan_id}", headers=auth_headers)).json()
    assert Decimal(detail["remaining_principal"]) == 1000
    assert sum(item["reported_paid"] for item in detail["schedule"]) == 2
    backup = await client.get("/api/export/backup", headers=auth_headers)
    assert backup.status_code == 200
    with zipfile.ZipFile(io.BytesIO(backup.content)) as archive:
        rows = json.loads(archive.read("loans.json"))
        assert rows[0]["id"] == loan_id
        assert rows[0]["paid_installments"] == 2
    archive = await client.patch(f"/api/loans/{loan_id}", headers=auth_headers, json={"version": 2, "paid_installments": 2, "archived": True})
    assert archive.status_code == 200
    assert archive.json()["archived"] is True


async def test_cross_workspace_loan_is_not_readable_or_writable(client, auth_headers, session, test_user):
    from app.models.workspace import Workspace
    other = Workspace(id=uuid.uuid4(), name="Other", kind="personal", created_by_user_id=test_user.id, billing_owner_user_id=test_user.id)
    session.add(other)
    await session.flush()
    loan = Loan(workspace_id=other.id, user_id=test_user.id, **LoanCreate(**payload()).model_dump())
    session.add(loan)
    await session.commit()
    assert (await client.get("/api/loans", headers=auth_headers)).json() == []
    assert (await client.get(f"/api/loans/{loan.id}", headers=auth_headers)).status_code == 404
    assert (await client.patch(f"/api/loans/{loan.id}", headers=auth_headers, json={"version": 1, "paid_installments": 1})).status_code == 404


async def test_spending_plan_reserves_overdue_and_upcoming_but_not_reported_paid_or_archived(session, test_user, test_workspace):
    cash = Account(id=uuid.uuid4(), user_id=test_user.id, workspace_id=test_workspace.id, name="Cash", type="checking", currency=test_user.primary_currency, balance=Decimal(0))
    session.add(cash)
    await session.flush()
    session.add(Transaction(user_id=test_user.id, workspace_id=test_workspace.id, account_id=cash.id, description="Cash", amount=Decimal(2000), currency=cash.currency, type="credit", date=date.today(), source="manual", status="posted"))
    loan = Loan(workspace_id=test_workspace.id, user_id=test_user.id, **LoanCreate(**payload(currency=cash.currency, first_due_date="2020-01-31", paid_installments=2)).model_dump())
    session.add(loan)
    await session.commit()
    request = SpendingPlanRequest(obligations_reviewed=True)
    plan = await calculate_spending_plan(session, test_workspace.id, test_user.id, request)
    assert plan.loan_due_reserve == 1000
    assert plan.safe_to_spend == 1000
    loan.archived = True
    await session.commit()
    plan = await calculate_spending_plan(session, test_workspace.id, test_user.id, request)
    assert plan.loan_due_reserve == 0
    assert plan.safe_to_spend == 2000


async def test_missing_loan_fx_blocks_safe_to_spend(session, test_user, test_workspace):
    loan = Loan(workspace_id=test_workspace.id, user_id=test_user.id, **LoanCreate(**payload(currency="USD")).model_dump())
    session.add(loan)
    await session.commit()
    plan = await calculate_spending_plan(session, test_workspace.id, test_user.id, SpendingPlanRequest(obligations_reviewed=True))
    assert plan.safe_to_spend is None
    assert any("exchange rate" in item for item in plan.blockers)
