import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.accounts import router as accounts_router
from app.api.admin import router as admin_router, check_registration_enabled
from app.api.asset_groups import router as asset_groups_router
from app.api.assets import router as assets_router
from app.api.attachments import router as attachments_router
from app.api.billing import router as billing_router
from app.api.budgets import router as budgets_router
from app.api.categories import router as categories_router
from app.api.category_groups import router as category_groups_router
from app.api.collections import router as collections_router
from app.api.connections import router as connections_router
from app.api.currencies import router as currencies_router
from app.api.custom_auth import router as custom_auth_router
from app.api.dashboard import router as dashboard_router
from app.api.export import router as export_router
from app.api.fiscal import router as fiscal_router
from app.api.fx_rates import router as fx_rates_router
from app.api.goals import router as goals_router
from app.api.groups import router as groups_router
from app.api.import_logs import router as import_logs_router
from app.api.import_transactions import router as import_router
from app.api.info import router as info_router
from app.api.invoice_attachments import router as invoice_attachments_router
from app.api.invoices import router as invoices_router
from app.api.oidc_auth import router as oidc_auth_router
from app.api.passkeys import router as passkeys_router
from app.api.payees import router as payees_router
from app.api.public_invoices import router as public_invoices_router
from app.api.reconciliation import router as reconciliation_router
from app.api.recurring_transactions import router as recurring_router
from app.api.reports import router as reports_router
from app.api.rules import router as rules_router
from app.api.search import router as search_router
from app.api.settings import router as settings_router
from app.api.setup import router as setup_router
from app.api.transactions import router as transactions_router
from app.api.two_factor import router as two_factor_router
from app.api.user_lookup import router as user_lookup_router
from app.api.workspaces import router as workspaces_router
from app.billing.guards import (
    accounts_guard,
    agents_guard,
    assets_guard,
    budgets_guard,
    goals_guard,
    groups_guard,
    imports_guard,
    invoices_guard,
    reconciliation_guard,
    recurring_guard,
    reports_guard,
    rules_guard,
    workspace_guard,
)
from app.core.auth import fastapi_users
from app.core.auth_policy import require_local_auth_enabled
from app.core.config import get_settings
from app.core.database import async_session_maker
from app.core.rate_limit import login_rate_limit, password_reset_rate_limit, register_rate_limit
from app.core.redis import close_redis, get_redis
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services.fx_rate_service import FxRateUnavailableError

logger = logging.getLogger(__name__)
settings = get_settings()


async def _warm_tesouro_cache() -> None:
    """Pre-load the Tesouro Direto price cache for BRL workspaces only."""
    try:
        if not get_settings().tesouro_direto_enabled:
            return
        from sqlalchemy import select

        from app.models.workspace import Workspace

        async with async_session_maker() as session:
            has_brl = await session.scalar(
                select(Workspace.id).where(Workspace.default_currency == "BRL").limit(1)
            )
        if not has_brl:
            return

        from app.providers.tesouro_direto import get_tesouro_direto_provider

        await get_tesouro_direto_provider().get_available_bonds()
        logger.info("Startup: warmed Tesouro Direto price cache")
    except Exception:
        logger.exception("Startup: Tesouro Direto cache warm failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Do not dispatch global bank-sync work from every API replica at startup.
    # Celery Beat is the single scheduler; on-demand syncs are individual jobs.
    app.state.tesouro_warm_task = asyncio.create_task(_warm_tesouro_cache())
    yield
    warm_task = getattr(app.state, "tesouro_warm_task", None)
    if warm_task and not warm_task.done():
        warm_task.cancel()
    await close_redis()


app = FastAPI(
    title=settings.app_name,
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(FxRateUnavailableError)
async def fx_rate_unavailable_handler(_request, exc: FxRateUnavailableError):
    """Never turn a missing FX rate into a believable-but-wrong money value."""
    return JSONResponse(
        status_code=503,
        content={
            "detail": "A required exchange rate is temporarily unavailable. No estimated 1:1 conversion was used.",
            "code": "fx_rate_unavailable",
            "from_currency": exc.from_currency,
            "to_currency": exc.to_currency,
            "date": exc.target_date.isoformat() if exc.target_date else None,
        },
        headers={"Retry-After": "60"},
    )


app.include_router(
    custom_auth_router,
    prefix="/api/auth",
    tags=["auth"],
    dependencies=[Depends(login_rate_limit)],
)
app.include_router(two_factor_router, prefix="/api/auth", tags=["auth"])
app.include_router(passkeys_router, prefix="/api/auth", tags=["auth"])
app.include_router(oidc_auth_router)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/api/auth",
    tags=["auth"],
    dependencies=[
        Depends(require_local_auth_enabled),
        Depends(check_registration_enabled),
        Depends(register_rate_limit),
    ],
)
app.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/api/auth",
    tags=["auth"],
    dependencies=[Depends(require_local_auth_enabled), Depends(password_reset_rate_limit)],
)
app.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/api/auth",
    tags=["auth"],
    dependencies=[Depends(require_local_auth_enabled), Depends(password_reset_rate_limit)],
)
app.include_router(user_lookup_router)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/api/users",
    tags=["users"],
)

# Domain routes. Billing guards are attached at the router boundary so hidden
# controls and direct HTTP requests share the same server-side policy.
app.include_router(billing_router)
app.include_router(categories_router)
app.include_router(category_groups_router)
app.include_router(rules_router, dependencies=[Depends(rules_guard)])
app.include_router(reconciliation_router, dependencies=[Depends(reconciliation_guard)])
app.include_router(transactions_router)
app.include_router(import_router, dependencies=[Depends(imports_guard)])
app.include_router(import_logs_router)
app.include_router(accounts_router, dependencies=[Depends(accounts_guard)])
app.include_router(connections_router)
app.include_router(recurring_router, dependencies=[Depends(recurring_guard)])
app.include_router(budgets_router, dependencies=[Depends(budgets_guard)])
app.include_router(goals_router, dependencies=[Depends(goals_guard)])
app.include_router(groups_router, dependencies=[Depends(groups_guard)])
app.include_router(assets_router, dependencies=[Depends(assets_guard)])
app.include_router(asset_groups_router)
app.include_router(collections_router)
app.include_router(dashboard_router)
app.include_router(reports_router, dependencies=[Depends(reports_guard)])
app.include_router(search_router)
app.include_router(setup_router)
app.include_router(currencies_router)
app.include_router(fx_rates_router)
app.include_router(export_router)
app.include_router(attachments_router)
app.include_router(fiscal_router)
app.include_router(payees_router)
app.include_router(invoices_router, dependencies=[Depends(invoices_guard)])
app.include_router(invoice_attachments_router, dependencies=[Depends(invoices_guard)])
app.include_router(public_invoices_router)
app.include_router(settings_router)
app.include_router(workspaces_router, dependencies=[Depends(workspace_guard)])
app.include_router(admin_router)
app.include_router(info_router)


if os.getenv("AGENTS_ENABLED", "false").strip().lower() in ("1", "true", "yes", "on"):
    try:
        from app.agents.api.agents import router as agents_router
        from app.agents.api.chat import router as agents_chat_router
        from app.agents.api.connections import router as agents_connections_router
        from app.agents.api.conversations import router as agents_conversations_router
        from app.agents.api.info import router as agents_info_router
        from app.agents.api.knowledge import router as agents_knowledge_router
        from app.agents.api.mcp_tokens import router as agents_mcp_tokens_router

        app.include_router(agents_info_router)
        app.include_router(agents_connections_router, dependencies=[Depends(agents_guard)])
        app.include_router(agents_conversations_router, dependencies=[Depends(agents_guard)])
        app.include_router(agents_mcp_tokens_router, dependencies=[Depends(agents_guard)])
        app.include_router(agents_router, dependencies=[Depends(agents_guard)])
        app.include_router(agents_chat_router, dependencies=[Depends(agents_guard)])
        app.include_router(agents_knowledge_router, dependencies=[Depends(agents_guard)])
        logger.info("Agents feature enabled — mounted /api/agents routes")
    except Exception:
        logger.exception("Agents feature flag is on but import failed; routes not mounted")


@app.get("/api/health")
@app.get("/api/health/live")
async def health_check():
    """Process liveness only. Dependency health belongs to readiness."""
    return {"status": "healthy"}


@app.get("/api/health/ready")
async def readiness_check():
    """Dependency-aware readiness used by orchestrators before routing traffic."""
    checks: dict[str, dict[str, object]] = {}
    ready = True

    try:
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = {"ok": True}
    except Exception as exc:
        logger.exception("Readiness database check failed")
        checks["database"] = {"ok": False, "error": type(exc).__name__}
        ready = False

    try:
        redis = await get_redis()
        await redis.ping()
        checks["redis"] = {"ok": True}
    except Exception as exc:
        logger.exception("Readiness Redis check failed")
        checks["redis"] = {"ok": False, "error": type(exc).__name__}
        ready = False

    fx_ok = bool(settings.openexchangerates_app_id.strip()) or not settings.require_fx_provider
    checks["fx_provider"] = {
        "ok": fx_ok,
        "required": settings.require_fx_provider,
        "configured": bool(settings.openexchangerates_app_id.strip()),
    }
    if not fx_ok:
        ready = False

    return JSONResponse(
        status_code=200 if ready else 503,
        content={"status": "ready" if ready else "not_ready", "checks": checks},
    )


from app.core.metrics import metrics, record_request  # noqa: E402
app.add_api_route("/metrics", metrics, methods=["GET"], include_in_schema=False)


@app.middleware("http")
async def request_metrics(request, call_next):
    try:
        response = await call_next(request)
    except Exception:
        record_request(request.method, 500)
        raise
    record_request(request.method, response.status_code)
    return response
