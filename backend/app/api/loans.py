import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.workspace_context import WorkspaceContext, current_workspace, current_writable_workspace
from app.models.loan import Loan
from app.models.workspace import Workspace
from app.schemas.loan import LoanCreate, LoanDetail, LoanRead, LoanUpdate
from app.services.loan_service import amortize

router = APIRouter(prefix="/api/loans", tags=["loans"])


@router.get("", response_model=list[LoanRead])
async def list_loans(
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    return (await session.scalars(select(Loan).where(Loan.workspace_id == ctx.id).order_by(Loan.updated_at.desc(), Loan.id))).all()


@router.post("", response_model=LoanRead, status_code=201)
async def create_loan(
    data: LoanCreate,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    # Serialize the workspace cap; a concurrent request cannot overrun it.
    await session.execute(select(Workspace.id).where(Workspace.id == ctx.id).with_for_update())
    count = await session.scalar(select(func.count()).select_from(Loan).where(Loan.workspace_id == ctx.id))
    if count is not None and count >= 100:
        raise HTTPException(409, "This workspace has reached its 100 loan-plan limit")
    row = Loan(workspace_id=ctx.id, user_id=ctx.user_id, **data.model_dump())
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


@router.get("/{loan_id}", response_model=LoanDetail)
async def get_loan(
    loan_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    row = await session.scalar(select(Loan).where(Loan.id == loan_id, Loan.workspace_id == ctx.id))
    if row is None:
        raise HTTPException(404, "Loan plan not found")
    loan = LoanRead.model_validate(row)
    schedule = amortize(loan)
    remaining = loan.principal if loan.paid_installments == 0 else schedule[loan.paid_installments - 1].remaining_principal
    return LoanDetail(
        loan=loan, schedule=schedule, monthly_payment=schedule[0].payment,
        total_interest=sum((item.interest for item in schedule), start=loan.principal * 0),
        remaining_principal=remaining,
    )


@router.patch("/{loan_id}", response_model=LoanRead)
async def update_loan(
    loan_id: uuid.UUID,
    data: LoanUpdate,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    row = await session.scalar(select(Loan).where(Loan.id == loan_id, Loan.workspace_id == ctx.id))
    if row is None:
        raise HTTPException(404, "Loan plan not found")
    if data.paid_installments > row.term_months:
        raise HTTPException(422, "Paid installments cannot exceed the loan term")
    # Compare-and-swap works on PostgreSQL and SQLite; never silently lose an edit.
    result = await session.execute(
        update(Loan).where(Loan.id == loan_id, Loan.workspace_id == ctx.id, Loan.version == data.version)
        .values(paid_installments=data.paid_installments, archived=data.archived, version=Loan.version + 1)
        .returning(Loan.id)
    )
    if result.scalar_one_or_none() is None:
        await session.rollback()
        raise HTTPException(409, "Loan plan changed. Reload before updating.")
    await session.commit()
    await session.refresh(row)
    return row
