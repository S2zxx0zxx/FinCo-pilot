import asyncio
import logging
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import quote

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _send_message(message: EmailMessage) -> None:
    settings = get_settings()
    if settings.smtp_use_ssl:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(
            settings.smtp_host,
            settings.smtp_port,
            timeout=20,
            context=context,
        ) as smtp:
            if settings.smtp_username:
                smtp.login(
                    settings.smtp_username,
                    settings.smtp_password.get_secret_value(),
                )
            smtp.send_message(message)
        return

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        smtp.ehlo()
        if settings.smtp_starttls:
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()
        if settings.smtp_username:
            smtp.login(
                settings.smtp_username,
                settings.smtp_password.get_secret_value(),
            )
        smtp.send_message(message)


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
            raise RuntimeError("Transactional email is required but SMTP is not configured")
        logger.warning("Transactional email skipped because SMTP is not configured")
        return False

    message = EmailMessage()
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(text_body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    try:
        await asyncio.to_thread(_send_message, message)
        return True
    except Exception:
        logger.exception("Transactional email delivery failed")
        if settings.email_delivery_required:
            raise
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
            f'<p><a href="{url}">Reset your password</a></p>'
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
            f'<p><a href="{url}">Verify email</a></p>'
            "<p>If you did not create this account, you can ignore this email.</p>"
        ),
    )
