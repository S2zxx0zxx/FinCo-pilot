import logging
import re
import secrets
import time
import uuid
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.enums import PlanId
from app.billing.service import get_effective_plan
from app.core.config import ZOHO_DESK_API_HOSTS, get_settings
from app.core.redis import get_redis
from app.models.user import User
from app.schemas.support import SupportCategory, SupportTicketCreate

logger = logging.getLogger(__name__)


class SupportDeliveryError(RuntimeError):
    """The external helpdesk did not confirm ticket creation."""


@dataclass(frozen=True)
class SupportRouting:
    severity: str
    support_tier: str
    provider_priority: str


@dataclass(frozen=True)
class CreatedSupportTicket:
    reference: str
    ticket_id: str
    ticket_number: str | None
    support_tier: str
    priority: str


_SEVERITY = {
    SupportCategory.ACCOUNT_ACCESS: "high",
    SupportCategory.BILLING_PAYMENT: "high",
    SupportCategory.BANK_CONNECTION: "normal",
    SupportCategory.TRANSACTIONS_IMPORT: "normal",
    SupportCategory.SAFE_TO_SPEND: "high",
    SupportCategory.FINCO_COPILOT: "normal",
    SupportCategory.BUG_PERFORMANCE: "normal",
    SupportCategory.PRIVACY_DATA: "high",
    SupportCategory.FEATURE_REQUEST: "low",
    SupportCategory.OTHER: "normal",
}

_TIER = {
    PlanId.FREE: "standard",
    PlanId.PRO: "priority",
    PlanId.MAX: "highest_priority",
}

# High-confidence credential patterns only. Users may legitimately write words
# such as "password" or "OTP"; block them only when they appear to include the
# secret value itself. Support copy separately warns against sharing sensitive
# financial/authentication data.
_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "authentication secret",
        re.compile(
            r"(?i)\b(password|passcode|pin|otp|cvv|cvc|api[_ -]?key|"
            r"access[_ -]?token|refresh[_ -]?token|client[_ -]?secret)\b"
            r"\s*[:=]\s*[^\s,;]{3,}"
        ),
    ),
    (
        "bearer token",
        re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{16,}"),
    ),
    (
        "JWT",
        re.compile(
            r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"
        ),
    ),
    (
        "API token",
        re.compile(r"\b(?:sk|rk|pk)-[A-Za-z0-9_-]{16,}\b"),
    ),
)


def make_support_reference() -> str:
    return "FC-" + secrets.token_hex(5).upper()


def find_sensitive_content(*values: str | None) -> list[str]:
    text = "\n".join(value or "" for value in values)
    found: list[str] = []
    for label, pattern in _SECRET_PATTERNS:
        if pattern.search(text):
            found.append(label)
    return found


def support_routing(plan: PlanId, category: SupportCategory) -> SupportRouting:
    severity = _SEVERITY[category]
    tier = _TIER[plan]

    # Severity always wins over commercial tier. A Free user's account-access,
    # privacy or money-integrity incident must not sit behind a Max user's
    # feature request. Plan tier only breaks ties inside lower-severity work.
    if severity == "high":
        provider_priority = "High"
    elif severity == "normal":
        provider_priority = {
            PlanId.FREE: "Low",
            PlanId.PRO: "Medium",
            PlanId.MAX: "High",
        }[plan]
    else:
        provider_priority = {
            PlanId.FREE: "Low",
            PlanId.PRO: "Low",
            PlanId.MAX: "Medium",
        }[plan]

    return SupportRouting(
        severity=severity,
        support_tier=tier,
        provider_priority=provider_priority,
    )


async def enforce_support_rate_limit(user_id: uuid.UUID) -> None:
    """Bound direct ticket creation with a concurrency-safe fixed UTC-hour bucket."""
    settings = get_settings()
    redis = await get_redis()
    now = time.time()
    window_seconds = 3600
    bucket = int(now // window_seconds)
    key = f"rate_limit:support:{user_id}:{bucket}"

    # Redis INCR is atomic across API replicas. The bucket key changes at the
    # hour boundary, so rejected requests cannot keep extending the user's
    # lockout window. A small cleanup buffer is harmless and bounds storage.
    count = int(await redis.incr(key))
    retry_after = max(1, int(((bucket + 1) * window_seconds) - now))
    await redis.expire(key, retry_after + 60)

    if count > settings.support_rate_limit_per_hour:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "SUPPORT_RATE_LIMITED",
                "message": "Too many support requests. Please use the support portal or email if the issue is urgent.",
            },
            headers={"Retry-After": str(retry_after)},
        )


def _trusted_zoho_api_domain(value: str, fallback: str) -> str:
    """Accept only exact Zoho Desk data-center origins returned by OAuth."""
    candidate = value.strip() or fallback.strip()
    parsed = urlsplit(candidate)
    hostname = (parsed.hostname or "").lower()
    trusted = (
        parsed.scheme == "https"
        and hostname in ZOHO_DESK_API_HOSTS
        and parsed.username is None
        and parsed.password is None
        and parsed.port in {None, 443}
        and parsed.path in {"", "/"}
        and not parsed.query
        and not parsed.fragment
    )
    if not trusted:
        logger.error("Zoho returned an unexpected API domain; using configured domain")
        return fallback.rstrip("/")
    return candidate.rstrip("/")


class ZohoDeskClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def _access_token(self, client: httpx.AsyncClient) -> tuple[str, str]:
        settings = self.settings
        response = await client.post(
            f"{settings.zoho_desk_accounts_domain.rstrip('/')}/oauth/v2/token",
            data={
                "refresh_token": settings.zoho_desk_refresh_token.get_secret_value(),
                "client_id": settings.zoho_desk_client_id,
                "client_secret": settings.zoho_desk_client_secret.get_secret_value(),
                "grant_type": "refresh_token",
            },
        )
        response.raise_for_status()
        payload = response.json()
        token = payload.get("access_token")
        if not isinstance(token, str) or not token:
            raise SupportDeliveryError("Zoho token response did not contain an access token")
        api_domain = _trusted_zoho_api_domain(
            str(payload.get("api_domain") or ""),
            settings.zoho_desk_api_domain,
        )
        return token, api_domain

    async def create_ticket(
        self,
        *,
        requester_email: str,
        subject: str,
        description: str,
        priority: str,
    ) -> tuple[str, str | None]:
        settings = self.settings
        timeout = httpx.Timeout(15.0, connect=8.0)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                token, api_domain = await self._access_token(client)
                response = await client.post(
                    f"{api_domain}/api/v1/tickets",
                    headers={
                        "Authorization": f"Zoho-oauthtoken {token}",
                        "orgId": settings.zoho_desk_org_id,
                        "Content-Type": "application/json",
                    },
                    json={
                        "departmentId": settings.zoho_desk_department_id,
                        "subject": subject,
                        "description": description,
                        "email": requester_email,
                        "channel": "Web",
                        "priority": priority,
                        "status": "Open",
                    },
                )
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            # Never include response bodies: providers can echo user content or
            # operational identifiers. Secrets are never part of this log line.
            logger.exception("Support provider ticket creation failed: %s", type(exc).__name__)
            raise SupportDeliveryError("Support provider did not confirm ticket creation") from exc

        ticket_id = payload.get("id")
        if not isinstance(ticket_id, str) or not ticket_id:
            raise SupportDeliveryError("Support provider returned no ticket id")
        number = payload.get("ticketNumber")
        return ticket_id, str(number) if number is not None else None


def _ticket_description(
    *,
    ticket: SupportTicketCreate,
    user: User,
    plan: PlanId,
    routing: SupportRouting,
    reference: str,
    request_reference: str,
    user_agent: str,
) -> str:
    diagnostics = [
        "--- FinCopilot diagnostic context (no financial records attached) ---",
        f"Reference: {reference}",
        f"Request reference: {request_reference}",
        f"User ID: {user.id}",
        f"Plan: {plan.value}",
        f"Support tier: {routing.support_tier}",
        f"Severity: {routing.severity}",
        f"Category: {ticket.category.value}",
        f"Page: {ticket.page_path or 'not supplied'}",
        f"App version: {ticket.app_version or 'not supplied'}",
        f"Locale: {ticket.locale or 'not supplied'}",
        f"Previous error reference: {ticket.error_reference or 'not supplied'}",
        f"User-Agent: {user_agent[:500] or 'not supplied'}",
        "--- End diagnostic context ---",
    ]
    return ticket.message + "\n\n" + "\n".join(diagnostics)


async def create_support_ticket(
    *,
    session: AsyncSession,
    user: User,
    ticket: SupportTicketCreate,
    request_reference: str,
    user_agent: str,
) -> CreatedSupportTicket:
    settings = get_settings()
    if not settings.support_ticket_submission_available:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "SUPPORT_DIRECT_SUBMISSION_UNAVAILABLE",
                "message": "Direct support submission is unavailable. Use the configured support portal or email.",
            },
        )

    sensitive = find_sensitive_content(ticket.subject, ticket.message)
    if sensitive:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "SUPPORT_SENSITIVE_CONTENT",
                "message": (
                    "Remove passwords, OTPs, PINs, CVV/CVC values, API keys or tokens "
                    "before sending this support request."
                ),
                "detected": sensitive,
            },
        )

    await enforce_support_rate_limit(user.id)

    plan = await get_effective_plan(session, user.id)
    routing = support_routing(plan, ticket.category)
    reference = make_support_reference()
    description = _ticket_description(
        ticket=ticket,
        user=user,
        plan=plan,
        routing=routing,
        reference=reference,
        request_reference=request_reference,
        user_agent=user_agent,
    )

    provider = ZohoDeskClient()
    try:
        ticket_id, ticket_number = await provider.create_ticket(
            requester_email=user.email,
            subject=f"[{reference}] {ticket.subject}",
            description=description,
            priority=routing.provider_priority,
        )
    except SupportDeliveryError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "SUPPORT_PROVIDER_UNAVAILABLE",
                "message": (
                    "The support provider did not confirm ticket creation. "
                    "No automatic retry was attempted to avoid duplicate tickets."
                ),
                "reference": reference,
            },
        ) from exc

    logger.info(
        "Support ticket created reference=%s provider_ticket=%s user=%s category=%s tier=%s",
        reference,
        ticket_id,
        user.id,
        ticket.category.value,
        routing.support_tier,
    )
    return CreatedSupportTicket(
        reference=reference,
        ticket_id=ticket_id,
        ticket_number=ticket_number,
        support_tier=routing.support_tier,
        priority=routing.provider_priority,
    )
