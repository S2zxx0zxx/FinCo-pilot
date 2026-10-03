"""Shared SMTP policy; never include provider responses or message data in errors."""
from __future__ import annotations

import smtplib
import ssl
from contextlib import contextmanager
from typing import TYPE_CHECKING, Iterator

from pydantic import EmailStr, TypeAdapter, ValidationError

if TYPE_CHECKING:
    from app.core.config import Settings


class EmailDeliveryError(RuntimeError):
    """Sanitized SMTP failure with a bounded, non-sensitive reason."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Transactional email unavailable ({reason})")


def mailbox(value: str) -> str:
    # One envelope recipient only: display names/lists/header injection are not
    # valid input. SMTPUTF8 handling remains delegated to smtplib.
    if not value or any(c in value for c in "\r\n\x00<>,;"):
        raise ValueError("Email address must be one bare mailbox")
    try:
        return str(TypeAdapter(EmailStr).validate_python(value))
    except ValidationError:
        raise ValueError("Email address must be one valid mailbox") from None


def validate_smtp_settings(settings: Settings) -> None:
    host = settings.smtp_host
    if host and (host != host.strip() or any(c.isspace() for c in host) or any(c in host for c in "/@?#\x00")):
        raise ValueError("SMTP_HOST must be a hostname or IP without URL/credentials")
    if settings.smtp_from_email:
        mailbox(settings.smtp_from_email)
    if bool(settings.smtp_username) != bool(settings.smtp_password.get_secret_value()):
        raise ValueError("SMTP_USERNAME and SMTP_PASSWORD must be configured together")
    if any(c in settings.smtp_username for c in "\r\n\x00"):
        raise ValueError("SMTP_USERNAME contains invalid control characters")
    if not 1 <= settings.smtp_timeout_seconds <= 60:
        raise ValueError("SMTP_TIMEOUT_SECONDS must be between 1 and 60")
    if not 1 <= settings.smtp_max_concurrent_sends <= 16:
        raise ValueError("SMTP_MAX_CONCURRENT_SENDS must be between 1 and 16")
    if settings.smtp_use_ssl and settings.smtp_starttls:
        raise ValueError("SMTP_USE_SSL and SMTP_STARTTLS cannot both be true")
    if not 1 <= settings.smtp_port <= 65535:
        raise ValueError("SMTP_PORT must be between 1 and 65535")
    if settings.is_production:
        if settings.local_auth_enabled and not settings.email_delivery_required:
            raise ValueError("Production local auth requires EMAIL_DELIVERY_REQUIRED=true")
        if settings.email_delivery_required and not settings.email_delivery_available:
            raise ValueError("Production email requires SMTP_HOST and SMTP_FROM_EMAIL")
        if host:
            if not (settings.smtp_use_ssl or settings.smtp_starttls):
                raise ValueError("Production SMTP requires verified TLS: SMTP_USE_SSL or SMTP_STARTTLS")
            if not settings.smtp_username:
                raise ValueError("Production SMTP requires authenticated SMTP_USERNAME and SMTP_PASSWORD")


def failure_reason(exc: Exception) -> str:
    if isinstance(exc, EmailDeliveryError):
        return exc.reason
    if isinstance(exc, ssl.SSLError):
        return "tls"
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return "authentication"
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return "recipient_refused"
    if isinstance(exc, smtplib.SMTPSenderRefused):
        return "sender_refused"
    if isinstance(exc, smtplib.SMTPDataError):
        return "data_refused"
    if isinstance(exc, smtplib.SMTPNotSupportedError):
        return "unsupported_protocol"
    if isinstance(exc, TimeoutError):
        return "timeout"
    if isinstance(exc, (OSError, smtplib.SMTPException)):
        return "transport"
    return "internal"


@contextmanager
def smtp_connection(settings: Settings) -> Iterator[smtplib.SMTP]:
    """TLS before AUTH/DATA, exact certificate verification, no retry on ambiguity."""
    validate_smtp_settings(settings)
    smtp: smtplib.SMTP | None = None
    try:
        context = ssl.create_default_context(cafile=settings.smtp_ssl_ca_file or None)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        if settings.smtp_use_ssl:
            smtp = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port,
                                    timeout=settings.smtp_timeout_seconds, context=context)
        else:
            smtp = smtplib.SMTP(settings.smtp_host, settings.smtp_port,
                                timeout=settings.smtp_timeout_seconds)
        code, _ = smtp.ehlo()
        if code != 250:
            raise EmailDeliveryError("greeting")
        if settings.smtp_starttls:
            smtp.starttls(context=context)
            code, _ = smtp.ehlo()
            if code != 250:
                raise EmailDeliveryError("greeting")
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password.get_secret_value())
        yield smtp
    finally:
        if smtp is not None:
            # DATA's positive completion, not QUIT, decides acceptance. A lost
            # QUIT response after acceptance must not encourage duplicate sends.
            try:
                smtp.quit()
            except (OSError, smtplib.SMTPException):
                pass
            finally:
                smtp.close()
