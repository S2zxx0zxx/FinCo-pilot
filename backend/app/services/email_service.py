import asyncio
import logging
import threading
from email.utils import formatdate, make_msgid
from html import escape
from email.message import EmailMessage
from urllib.parse import quote

from app.core.config import get_settings
from app.core.smtp_runtime import EmailDeliveryError, failure_reason, mailbox, smtp_connection

logger = logging.getLogger(__name__)


# Capacity is held by the worker until the socket closes, including after an
# async caller disconnects. There is no unbounded mail queue or raw-token outbox.
_capacity_lock = threading.Lock()
_active_sends = 0
_pending_tasks: set[asyncio.Task] = set()


def _send_message(message: EmailMessage) -> None:
    with smtp_connection(get_settings()) as smtp:
        refused = smtp.send_message(message, from_addr=str(message["From"]),
                                    to_addrs=[str(message["To"])])
        if refused:
            raise EmailDeliveryError("recipient_refused")


def _deliver_reserved(message: EmailMessage) -> None:
    global _active_sends
    try:
        _send_message(message)
    except Exception as exc:
        reason = failure_reason(exc)
        logger.warning("Transactional email submission failed (%s)", reason)
        raise EmailDeliveryError(reason) from None
    finally:
        with _capacity_lock:
            _active_sends -= 1


async def send_email(
    *,
    recipient: str,
    subject: str,
    text_body: str,
    html_body: str | None = None,
) -> bool:
    """Send one transactional email without blocking the API event loop.

    Returns False only when email is intentionally optional and not configured.
    Required production deployments fail visibly rather than pretending a reset
    or verification message was delivered.
    """
    settings = get_settings()
    if not settings.email_delivery_available:
        if settings.email_delivery_required:
            raise EmailDeliveryError("not_configured")
        logger.warning("Transactional email skipped because SMTP is not configured")
        return False

    message = EmailMessage()
    message["From"] = mailbox(settings.smtp_from_email)
    message["To"] = mailbox(recipient)
    message["Subject"] = subject
    message["Date"] = formatdate(localtime=False, usegmt=True)
    message["Message-ID"] = make_msgid(domain=str(message["From"]).rsplit("@", 1)[1])
    message["Auto-Submitted"] = "auto-generated"
    message.set_content(text_body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    global _active_sends
    with _capacity_lock:
        reserved = _active_sends < settings.smtp_max_concurrent_sends
        if reserved:
            _active_sends += 1
    if not reserved:
        if settings.email_delivery_required:
            raise EmailDeliveryError("capacity")
        return False
    # Keep a task alive when the HTTP caller is cancelled: cancelling to_thread
    # cannot stop its socket, nor may it release the capacity slot prematurely.
    task = asyncio.create_task(asyncio.to_thread(_deliver_reserved, message))
    _pending_tasks.add(task)
    def consume_result(completed: asyncio.Task) -> None:
        _pending_tasks.discard(completed)
        if not completed.cancelled():
            completed.exception()
    task.add_done_callback(consume_result)
    try:
        await asyncio.shield(task)
        return True  # SMTP accepted; inbox delivery is not implied.
    except Exception as exc:
        reason = failure_reason(exc)
        if settings.email_delivery_required:
            raise EmailDeliveryError(reason) from None
        return False


async def send_password_reset_email(recipient: str, token: str) -> bool:
    settings = get_settings()
    url = f"{settings.frontend_url.rstrip('/')}/reset-password?token={quote(token, safe='')}"
    return await send_email(
        recipient=recipient,
        subject="Reset your FinCo-Pilot password",
        text_body=(
            "A password reset was requested for your FinCo-Pilot account.\n\n"
            f"Reset your password: {url}\n\n"
            "If you did not request this, you can ignore this email."
        ),
        html_body=(
            "<p>A password reset was requested for your FinCo-Pilot account.</p>"
            f'<p><a href="{escape(url, quote=True)}">Reset your password</a></p>'
            "<p>If you did not request this, you can ignore this email.</p>"
        ),
    )


async def send_verification_email(recipient: str, token: str) -> bool:
    settings = get_settings()
    url = f"{settings.frontend_url.rstrip('/')}/verify-email?token={quote(token, safe='')}"
    return await send_email(
        recipient=recipient,
        subject="Verify your FinCo-Pilot email",
        text_body=(
            "Verify the email address for your FinCo-Pilot account.\n\n"
            f"Verify email: {url}\n\n"
            "If you did not create this account, you can ignore this email."
        ),
        html_body=(
            "<p>Verify the email address for your FinCo-Pilot account.</p>"
            f'<p><a href="{escape(url, quote=True)}">Verify email</a></p>'
            "<p>If you did not create this account, you can ignore this email.</p>"
        ),
    )


async def send_password_changed_email(recipient: str) -> bool:
    return await send_email(
        recipient=recipient, subject="Your FinCo-Pilot password was changed",
        text_body="Your FinCo-Pilot password was changed. Sign in again using your new password. "
                  "If you did not make this change, contact support through your FinCo-Pilot app immediately.",
    )
