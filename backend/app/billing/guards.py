from __future__ import annotations

import uuid
from typing import Any

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.dependencies import require_workspace_capability
from app.billing.enums import Capability, Metric
from app.billing.usage import consume_monthly, enforce_limit, enforce_workspace_creation
from app.core.auth import current_active_user
from app.core.database import get_async_session
from app.core.workspace_context import WorkspaceContext, current_workspace
from app.models.asset import Asset
from app.models.goal import Goal
from app.models.group import Group
from app.models.recurring_transaction import RecurringTransaction
from app.models.rule import Rule
from app.models.user import User
from app.services import rule_service


def _path(request: Request) -> str:
    path = request.url.path.rstrip("/")
    return path or "/"


async def _json(request: Request) -> dict[str, Any]:
    try:
        value = await request.json()
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


async def accounts_guard(
    request: Request,
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    if request.method == "POST" and _path(request) == "/api/accounts":
        await enforce_limit(session, ctx.workspace, Metric.ACCOUNTS)


async def budgets_guard(
    request: Request,
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    if request.method == "POST" and _path(request) == "/api/budgets":
        await enforce_limit(session, ctx.workspace, Metric.ACTIVE_BUDGETS)


async def goals_guard(
    request: Request,
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    path = _path(request)
    if request.method == "POST" and path == "/api/goals":
        body = await _json(request)
        if body.get("status", "active") == "active":
            await enforce_limit(session, ctx.workspace, Metric.ACTIVE_GOALS)
        return
    if request.method == "PATCH" and path.startswith("/api/goals/"):
        body = await _json(request)
        if body.get("status") != "active":
            return
        raw_id = request.path_params.get("goal_id")
        try:
            goal_id = uuid.UUID(str(raw_id))
        except (TypeError, ValueError):
            return
        current = await session.get(Goal, goal_id)
        if current is not None and current.workspace_id == ctx.workspace.id and current.status != "active":
            await enforce_limit(session, ctx.workspace, Metric.ACTIVE_GOALS)


async def recurring_guard(
    request: Request,
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    path = _path(request)
    if request.method == "POST" and path == "/api/recurring-transactions":
        body = await _json(request)
        if body.get("is_active", True):
            await enforce_limit(session, ctx.workspace, Metric.ACTIVE_RECURRING)
        return
    if request.method == "PATCH" and path.startswith("/api/recurring-transactions/"):
        body = await _json(request)
        if body.get("is_active") is not True:
            return
        raw_id = request.path_params.get("recurring_id")
        try:
            recurring_id = uuid.UUID(str(raw_id))
        except (TypeError, ValueError):
            return
        current = await session.get(RecurringTransaction, recurring_id)
        if (
            current is not None
            and current.workspace_id == ctx.workspace.id
            and not current.is_active
        ):
            await enforce_limit(session, ctx.workspace, Metric.ACTIVE_RECURRING)


async def groups_guard(
    request: Request,
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    path = _path(request)
    if request.method == "POST" and path == "/api/groups":
        body = await _json(request)
        if not body.get("is_archived", False):
            await enforce_limit(session, ctx.workspace, Metric.ACTIVE_SPLIT_GROUPS)
        return

    if request.method == "POST" and path.endswith("/members") and path.startswith("/api/groups/"):
        raw_id = request.path_params.get("group_id")
        try:
            group_id = uuid.UUID(str(raw_id))
        except (TypeError, ValueError):
            return
        await enforce_limit(
            session,
            ctx.workspace,
            Metric.GROUP_MEMBERS,
            group_id=group_id,
        )
        return

    if request.method == "PATCH" and path.startswith("/api/groups/") and "/members/" not in path:
        body = await _json(request)
        if body.get("is_archived") is not False:
            return
        raw_id = request.path_params.get("group_id")
        try:
            group_id = uuid.UUID(str(raw_id))
        except (TypeError, ValueError):
            return
        current = await session.get(Group, group_id)
        if current is not None and current.workspace_id == ctx.workspace.id and current.is_archived:
            await enforce_limit(session, ctx.workspace, Metric.ACTIVE_SPLIT_GROUPS)


async def workspace_guard(
    request: Request,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    if request.method != "POST" or _path(request) != "/api/workspaces":
        return
    body = await _json(request)
    kind = str(body.get("kind", "personal"))
    await enforce_workspace_creation(session, user.id, kind=kind)


async def imports_guard(
    request: Request,
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    if request.method == "POST" and _path(request) == "/api/transactions/import":
        await consume_monthly(session, ctx.workspace, Metric.IMPORTS_MONTHLY)


async def assets_guard(
    request: Request,
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    path = _path(request)
    if request.method != "POST":
        return

    if path == "/api/assets":
        body = await _json(request)
        if not body.get("is_archived", False):
            await enforce_limit(session, ctx.workspace, Metric.ASSETS)
        return

    if path == "/api/assets/buy":
        body = await _json(request)
        ticker = str(body.get("ticker", "")).strip().upper()
        group_raw = body.get("group_id")
        group_id = None
        if group_raw:
            try:
                group_id = uuid.UUID(str(group_raw))
            except ValueError:
                group_id = None
        if ticker:
            result = await session.execute(
                select(Asset.id).where(
                    Asset.workspace_id == ctx.workspace.id,
                    Asset.ticker == ticker,
                    Asset.group_id == group_id,
                    Asset.is_archived.is_(False),
                ).limit(1)
            )
            if result.scalar_one_or_none() is None:
                await enforce_limit(session, ctx.workspace, Metric.ASSETS)
        return

    if path == "/api/assets/import":
        body = await _json(request)
        await consume_monthly(session, ctx.workspace, Metric.IMPORTS_MONTHLY)
        orders = body.get("orders") if isinstance(body.get("orders"), list) else []
        tickers = {
            str(order.get("ticker", "")).strip().upper()
            for order in orders
            if isinstance(order, dict) and str(order.get("ticker", "")).strip()
        }
        if not tickers:
            return
        group_raw = body.get("group_id")
        group_id = None
        if group_raw:
            try:
                group_id = uuid.UUID(str(group_raw))
            except ValueError:
                group_id = None
        existing_result = await session.execute(
            select(Asset.ticker).where(
                Asset.workspace_id == ctx.workspace.id,
                Asset.ticker.in_(tickers),
                Asset.group_id == group_id,
                Asset.is_archived.is_(False),
            )
        )
        existing = {str(value).upper() for value in existing_result.scalars().all() if value}
        new_count = len(tickers - existing)
        if new_count:
            await enforce_limit(session, ctx.workspace, Metric.ASSETS, increment=new_count)


async def rules_guard(
    request: Request,
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    path = _path(request)
    method = request.method
    if method in {"GET", "HEAD", "OPTIONS", "DELETE"}:
        return
    if method == "POST" and path == "/api/rules/preview":
        return

    await require_workspace_capability(session, ctx.workspace, Capability.RULES)

    if method == "POST" and path == "/api/rules":
        await enforce_limit(session, ctx.workspace, Metric.RULES)
        return

    if method == "POST" and path == "/api/rules/import":
        body = await _json(request)
        payload = body.get("payload") if isinstance(body.get("payload"), dict) else {}
        incoming = payload.get("rules") if isinstance(payload.get("rules"), list) else []
        names = {str(item.get("name", "")).strip() for item in incoming if isinstance(item, dict)}
        names.discard("")
        if not names:
            return
        existing_result = await session.execute(
            select(Rule.name).where(
                Rule.workspace_id == ctx.workspace.id,
                Rule.name.in_(names),
            )
        )
        existing = set(existing_result.scalars().all())
        new_count = len(names - existing)
        if new_count:
            await enforce_limit(session, ctx.workspace, Metric.RULES, increment=new_count)
        return

    if method == "POST" and path.startswith("/api/rules/packs/") and path.endswith("/install"):
        pack_code = str(request.path_params.get("pack_code", ""))
        pack = rule_service.RULE_PACKS.get(pack_code)
        if not pack:
            return
        names = {str(item.get("name", "")).strip() for item in pack.get("rules", [])}
        names.discard("")
        if not names:
            return
        existing_result = await session.execute(
            select(Rule.name).where(
                Rule.workspace_id == ctx.workspace.id,
                Rule.name.in_(names),
            )
        )
        existing = set(existing_result.scalars().all())
        new_count = len(names - existing)
        if new_count:
            await enforce_limit(session, ctx.workspace, Metric.RULES, increment=new_count)


async def reports_guard(
    request: Request,
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    if _path(request).startswith("/api/reports"):
        await require_workspace_capability(session, ctx.workspace, Capability.ADVANCED_REPORTS)


async def invoices_guard(
    request: Request,
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    method = request.method
    path = _path(request)
    if method in {"GET", "HEAD", "OPTIONS"}:
        return

    # Downgraded users keep cleanup/control of files already in their history.
    # Uploading another file grows paid storage/business data and stays Max-only;
    # rename/delete do not increase the paid resource and remain available.
    if "/attachments" in path and method in {"PATCH", "DELETE"}:
        return

    await require_workspace_capability(session, ctx.workspace, Capability.INVOICES)
    if method == "POST" and path == "/api/invoices":
        await consume_monthly(session, ctx.workspace, Metric.INVOICES_MONTHLY)


async def reconciliation_guard(
    request: Request,
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    await require_workspace_capability(session, ctx.workspace, Capability.SMART_RECONCILIATION)


async def agents_guard(
    request: Request,
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    """Max-only advanced agent guard; usage is consumed after chat validation."""
    await require_workspace_capability(session, ctx.workspace, Capability.AGENTS_AUTOMATION)
