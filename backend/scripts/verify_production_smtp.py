"""TLS/AUTH/NOOP acceptance by default. Sending requires an explicit recipient."""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.core.smtp_runtime import EmailDeliveryError, failure_reason, mailbox, smtp_connection
from app.services.email_service import send_email


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--send-test", action="store_true", help="Send one harmless message to an operator-controlled inbox")
    parser.add_argument("--recipient", help="Explicit operator-controlled mailbox; never a mailing list")
    args = parser.parse_args(argv)
    if args.send_test != bool(args.recipient):
        parser.error("--send-test and --recipient must be supplied together")
    try:
        settings = get_settings()
        if not settings.is_production:
            raise EmailDeliveryError("production_required")
        if not settings.email_delivery_available:
            raise EmailDeliveryError("not_configured")
        if args.send_test:
            recipient = mailbox(args.recipient)
            accepted = asyncio.run(send_email(
                recipient=recipient, subject="FinCo-Pilot SMTP acceptance test",
                text_body="This is an operator-requested FinCo-Pilot SMTP acceptance test. No financial data or authentication token is included. Verify provider status and inbox receipt separately.",
            ))
            if not accepted:
                raise EmailDeliveryError("not_accepted")
            print("FinCo-Pilot SMTP acceptance: PASS\nsubmission=accepted\ninbox_delivery=operator_verification_required")
        else:
            with smtp_connection(settings) as smtp:
                code, _ = smtp.noop()
                if code != 250:
                    raise EmailDeliveryError("noop")
            print("FinCo-Pilot SMTP connection: PASS\ntls_auth_noop=pass\nmessage_sent=false\ninbox_delivery=not_tested")
        return 0
    except Exception as exc:
        # ValidationError may include input values; never print repr/traceback.
        print(f"FinCo-Pilot SMTP acceptance: FAIL ({failure_reason(exc)})", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
