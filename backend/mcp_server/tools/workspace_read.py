"""Read-only Copilot surfaces that do not fit the original MCP v1 modules.

These tools expose user-visible application state only. They deliberately omit
provider credentials, raw bank payloads, external tokens, and other secrets.
All queries are scoped to the authenticated workspace from the MCP JWT.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bank_connection import BankConnection
from app.models.loan import Loan
from app.models.rule import Rule
from app.schemas.loan import LoanRead
from app.services import collection_service
from app.services.loan_service import amortize
from mcp_server.auth import CallContext
from mcp_server.registry import tool
from mcp_server.tools._helpers import num, resolve_workspace_id


@tool(
    name="list_loans",
    description=(
        "List the workspace's loan plans with deterministic repayment facts: "
        "principal, rate, paid installments, monthly payment estimate, remaining "
        "principal, and next unpaid due date. The loan engine currently models "
        "fixed-rate monthly repayment and does not infer lender-verified payments."
    ),
    parameters={
        "type": "object",
        "properties": {
            "include_archived": {"type": "boolean", "default": False},
        },
        "additionalProperties": False,
    },
    tags=["read", "loans"],
)
async def list_loans(
    *,
    session: AsyncSession,
    ctx: CallContext,
    include_archived: bool = False,
) -> dict[str, Any]:
    workspace_id = await resolve_workspace_id(session, ctx)
    query = select(Loan).where(Loan.workspace_id == workspace_id)
    if not include_archived:
        query = query.where(Loan.archived.is_(False))
    rows = list((await session.execute(
        query.order_by(Loan.updated_at.desc(), Loan.id)
    )).scalars().all())

    items: list[dict[str, Any]] = []
    for row in rows:
        loan = LoanRead.model_validate(row)
        schedule = amortize(loan)
        paid = max(0, min(loan.paid_installments, len(schedule)))
        remaining = (
            loan.principal
            if paid == 0
            else schedule[paid - 1].remaining_principal
        )
        next_due = next((item for item in schedule if not item.reported_paid), None)
        items.append({
            "id": str(loan.id),
            "name": loan.name,
            "principal": num(loan.principal),
            "annual_rate": num(loan.annual_rate),
            "term_months": loan.term_months,
            "paid_installments": loan.paid_installments,
            "currency": loan.currency,
            "first_due_date": loan.first_due_date.isoformat(),
            "archived": loan.archived,
            "monthly_payment": num(schedule[0].payment) if schedule else None,
            "remaining_principal": num(remaining),
            "next_unpaid_due_date": (
                next_due.due_date.isoformat() if next_due is not None else None
            ),
            "next_unpaid_payment": (
                num(next_due.payment) if next_due is not None else None
            ),
        })
    return {"items": items, "total": len(items)}


@tool(
    name="list_bank_connection_status",
    description=(
        "List bank/institution connection health and freshness for the current "
        "workspace. Returns safe metadata only; credentials, provider tokens, raw "
        "payloads, and external provider identifiers are never exposed."
    ),
    parameters={"type": "object", "properties": {}, "additionalProperties": False},
    tags=["read", "connections", "freshness"],
)
async def list_bank_connection_status(
    *,
    session: AsyncSession,
    ctx: CallContext,
) -> dict[str, Any]:
    workspace_id = await resolve_workspace_id(session, ctx)
    rows = list((await session.execute(
        select(BankConnection)
        .where(BankConnection.workspace_id == workspace_id)
        .order_by(BankConnection.created_at.desc(), BankConnection.id)
    )).scalars().all())
    items = []
    for row in rows:
        sync_status = row.last_sync_status or "idle"
        needs_attention = (
            row.status != "active"
            or sync_status in {"rate_limited", "action_required", "error"}
        )
        items.append({
            "id": str(row.id),
            "provider": row.provider,
            "institution": row.display_name or row.institution_name,
            "status": row.status,
            "last_sync_status": sync_status,
            "last_sync_at": row.last_sync_at.isoformat() if row.last_sync_at else None,
            "last_provider_refresh_at": (
                row.last_provider_refresh_at.isoformat()
                if row.last_provider_refresh_at
                else None
            ),
            "needs_attention": needs_attention,
        })
    return {"items": items, "total": len(items)}


@tool(
    name="list_rules",
    description=(
        "List the workspace's transaction automation/categorization rules and "
        "their exact conditions/actions. This is read-only; changing rules must "
        "go through the normal proposal/API entitlement path."
    ),
    parameters={
        "type": "object",
        "properties": {
            "active_only": {"type": "boolean", "default": False},
        },
        "additionalProperties": False,
    },
    tags=["read", "rules"],
)
async def list_rules(
    *,
    session: AsyncSession,
    ctx: CallContext,
    active_only: bool = False,
) -> dict[str, Any]:
    workspace_id = await resolve_workspace_id(session, ctx)
    query = select(Rule).where(Rule.workspace_id == workspace_id)
    if active_only:
        query = query.where(Rule.is_active.is_(True))
    rows = list((await session.execute(
        query.order_by(Rule.priority.asc(), Rule.id.asc())
    )).scalars().all())
    return {
        "items": [
            {
                "id": str(row.id),
                "name": row.name,
                "is_active": bool(row.is_active),
                "priority": row.priority,
                "conditions_op": row.conditions_op,
                "conditions": row.conditions or [],
                "actions": row.actions or [],
            }
            for row in rows
        ],
        "total": len(rows),
    }


@tool(
    name="list_collections",
    description=(
        "List the workspace's user-defined account/asset collections used for "
        "filtering, including member account and wallet ids."
    ),
    parameters={"type": "object", "properties": {}, "additionalProperties": False},
    tags=["read", "collections"],
)
async def list_collections(
    *,
    session: AsyncSession,
    ctx: CallContext,
) -> dict[str, Any]:
    workspace_id = await resolve_workspace_id(session, ctx)
    rows = await collection_service.get_collections(session, workspace_id)
    items = [
        row.model_dump(mode="json") if hasattr(row, "model_dump") else dict(row)
        for row in rows
    ]
    return {"items": items, "total": len(items)}
