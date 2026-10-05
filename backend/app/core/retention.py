"""Canonical retention policy contract for FinCo-Pilot.

Roadmap #9 establishes policy and machine-readable invariants.  It deliberately
does *not* implement personal-account deletion, shared-workspace deletion,
processor deletion, backup jobs, or legal-hold execution; those belong to later
roadmap items.

The constants below are operator engineering decisions unless a comment
explicitly says otherwise.  They are intentionally conservative enough to
support the current CERT-In logging direction and the announced future DPDP
Rules security/log-retention requirements without pretending that every future
DPDP obligation is already in force.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


POLICY_ID = "FINCO_DATA_RETENTION_V1"
POLICY_VERSION = "2026-10-02"

# Operator-selected engineering windows.
SECURITY_LOG_RETENTION_DAYS = 365
BACKUP_MAX_RETENTION_DAYS = 30
ORPHAN_BLOB_SWEEP_HOURS = 24
CLOSED_SUPPORT_TICKET_RETENTION_DAYS = 365
ABANDONED_CHECKOUT_RETENTION_DAYS = 30
AI_USAGE_RETENTION_DAYS = 365
SECURITY_APPROVAL_EVIDENCE_RETENTION_DAYS = 365
MCP_APPROVAL_ARGUMENT_RETENTION_DAYS = 30

# Legal/provider reference points.  These are anchors for policy validation,
# not a claim that every rule applies to every FinCo-Pilot deployment.
CERT_IN_ICT_LOG_REFERENCE_DAYS = 180
DPDP_FUTURE_LOG_REFERENCE_DAYS = 365
RAZORPAY_TRANSACTION_RECORD_REFERENCE_YEARS = 10
RAZORPAY_DEVICE_INVOICE_REFERENCE_MONTHS = 6
ZOHO_DESK_RECYCLE_BIN_DAYS = 60
ZOHO_DESK_BACKUP_AFTER_TRASH_DAYS = 90


class RetentionMode(str, Enum):
    """How a category reaches end-of-life."""

    ACTIVE_PURPOSE = "active_purpose"
    ROLLING_DAYS = "rolling_days"
    AFTER_TRIGGER_DAYS = "after_trigger_days"
    AFTER_TRIGGER_YEARS = "after_trigger_years"
    EPHEMERAL_TTL = "ephemeral_ttl"
    IMMEDIATE_ON_TRIGGER = "immediate_on_trigger"
    PROVIDER_MANAGED = "provider_managed"
    NOT_SERVER_PERSISTED = "not_server_persisted"


class DeletionMode(str, Enum):
    HARD_DELETE = "hard_delete"
    ANONYMIZE_OR_HARD_DELETE = "anonymize_or_hard_delete"
    REVOKE_THEN_DELETE = "revoke_then_delete"
    EXPIRE_BY_TTL = "expire_by_ttl"
    PROVIDER_DELETE = "provider_delete"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class RetentionRule:
    """Machine-readable minimum contract used by later lifecycle work."""

    key: str
    mode: RetentionMode
    deletion: DeletionMode
    days: int | None = None
    years: int | None = None
    backup_days: int | None = BACKUP_MAX_RETENTION_DAYS
    notes: str = ""


RETENTION_RULES: dict[str, RetentionRule] = {
    "primary_financial_workspace_data": RetentionRule(
        key="primary_financial_workspace_data",
        mode=RetentionMode.ACTIVE_PURPOSE,
        deletion=DeletionMode.HARD_DELETE,
        notes=(
            "Keep while the user/workspace purpose remains active. Account/workspace "
            "deletion semantics are implemented by roadmap #10/#11/#29/#30, not here."
        ),
    ),
    "attachments_and_invoice_documents": RetentionRule(
        key="attachments_and_invoice_documents",
        mode=RetentionMode.ACTIVE_PURPOSE,
        deletion=DeletionMode.HARD_DELETE,
        notes=(
            "Object bytes and DB metadata share the parent lifecycle. Unreferenced blobs "
            f"must be swept within {ORPHAN_BLOB_SWEEP_HOURS} hours once lifecycle jobs exist."
        ),
    ),
    "bank_connection_credentials": RetentionRule(
        key="bank_connection_credentials",
        mode=RetentionMode.IMMEDIATE_ON_TRIGGER,
        deletion=DeletionMode.REVOKE_THEN_DELETE,
        backup_days=BACKUP_MAX_RETENTION_DAYS,
        notes="Revoke upstream access and erase local credentials on disconnect/deletion.",
    ),
    "bank_synced_records": RetentionRule(
        key="bank_synced_records",
        mode=RetentionMode.ACTIVE_PURPOSE,
        deletion=DeletionMode.HARD_DELETE,
        notes="Provider-derived finance data follows the workspace/account lifecycle.",
    ),
    "authentication_challenges_and_rate_limits": RetentionRule(
        key="authentication_challenges_and_rate_limits",
        mode=RetentionMode.EPHEMERAL_TTL,
        deletion=DeletionMode.EXPIRE_BY_TTL,
        backup_days=None,
        notes="Redis-only temporary state must always have an explicit TTL and is never backed up.",
    ),
    "authentication_credentials_and_passkeys": RetentionRule(
        key="authentication_credentials_and_passkeys",
        mode=RetentionMode.ACTIVE_PURPOSE,
        deletion=DeletionMode.HARD_DELETE,
        notes="Keep only while the account/credential remains active.",
    ),
    "security_request_and_access_logs": RetentionRule(
        key="security_request_and_access_logs",
        mode=RetentionMode.ROLLING_DAYS,
        deletion=DeletionMode.HARD_DELETE,
        days=SECURITY_LOG_RETENTION_DAYS,
        notes="Security logs are minimised, secret-free, access-restricted and stored in India.",
    ),
    "support_tickets": RetentionRule(
        key="support_tickets",
        mode=RetentionMode.AFTER_TRIGGER_DAYS,
        deletion=DeletionMode.PROVIDER_DELETE,
        days=CLOSED_SUPPORT_TICKET_RETENTION_DAYS,
        backup_days=None,
        notes=(
            "Retain for the configured period after closure, then delete through the helpdesk "
            "provider. Provider recycle-bin and backup deletion tails are tracked separately."
        ),
    ),
    "successful_payment_and_subscription_evidence": RetentionRule(
        key="successful_payment_and_subscription_evidence",
        mode=RetentionMode.AFTER_TRIGGER_DAYS,
        deletion=DeletionMode.ANONYMIZE_OR_HARD_DELETE,
        days=SECURITY_LOG_RETENTION_DAYS,
        notes=(
            "Minimum internal evidence window after the service/payment relationship ends; "
            "longer retention requires a documented legal, tax, dispute, or legal-hold reason."
        ),
    ),
    "razorpay_transaction_order_records": RetentionRule(
        key="razorpay_transaction_order_records",
        mode=RetentionMode.AFTER_TRIGGER_YEARS,
        deletion=DeletionMode.ANONYMIZE_OR_HARD_DELETE,
        years=RAZORPAY_TRANSACTION_RECORD_REFERENCE_YEARS,
        notes=(
            "Current Razorpay Payments merchant terms require transaction/order records "
            "to be retained for 10 calendar years from the relevant order date when that "
            "contract applies. Retain only the minimum record set required by contract/law; "
            "never use this exception to preserve card PAN/CVV or unrelated product data. "
            "Payment activation grants retain minimal provider/quote/term evidence. Webhook receipts retain only allowlisted encrypted financial snapshots and "
            "provider identifiers; raw bodies/contact/card/custom-note data are not retained."
        ),
    ),
    "abandoned_checkout_reservations": RetentionRule(
        key="abandoned_checkout_reservations",
        mode=RetentionMode.AFTER_TRIGGER_DAYS,
        deletion=DeletionMode.HARD_DELETE,
        days=ABANDONED_CHECKOUT_RETENTION_DAYS,
        notes="Starts when the reservation expires or is abandoned.",
    ),
    "pricing_and_security_audit_events": RetentionRule(
        key="pricing_and_security_audit_events",
        mode=RetentionMode.ROLLING_DAYS,
        deletion=DeletionMode.ANONYMIZE_OR_HARD_DELETE,
        days=SECURITY_LOG_RETENTION_DAYS,
        notes="Keep the event evidence; minimise or detach actor identifiers when no longer required.",
    ),
    "mcp_token_and_approval_evidence": RetentionRule(
        key="mcp_token_and_approval_evidence",
        mode=RetentionMode.AFTER_TRIGGER_DAYS,
        deletion=DeletionMode.ANONYMIZE_OR_HARD_DELETE,
        days=SECURITY_APPROVAL_EVIDENCE_RETENTION_DAYS,
        notes=(
            "Keep minimal token/approval decision evidence after expiry, revocation, or "
            "terminal state. Bearer tokens and exact tool arguments are not evidence fields."
        ),
    ),
    "mcp_approval_argument_payloads": RetentionRule(
        key="mcp_approval_argument_payloads",
        mode=RetentionMode.AFTER_TRIGGER_DAYS,
        deletion=DeletionMode.ANONYMIZE_OR_HARD_DELETE,
        days=MCP_APPROVAL_ARGUMENT_RETENTION_DAYS,
        notes=(
            "Exact approved tool arguments are higher-sensitivity payloads. After the short "
            "window, redact or remove them while preserving only the minimal approval evidence."
        ),
    ),
    "ai_conversation_content": RetentionRule(
        key="ai_conversation_content",
        mode=RetentionMode.ACTIVE_PURPOSE,
        deletion=DeletionMode.HARD_DELETE,
        notes="User-controlled history: retain until conversation/account/workspace deletion.",
    ),
    "ai_knowledge_files_and_chunks": RetentionRule(
        key="ai_knowledge_files_and_chunks",
        mode=RetentionMode.ACTIVE_PURPOSE,
        deletion=DeletionMode.HARD_DELETE,
        notes="Raw file, extracted chunks and embeddings share the knowledge document lifecycle.",
    ),
    "ai_usage_telemetry": RetentionRule(
        key="ai_usage_telemetry",
        mode=RetentionMode.ROLLING_DAYS,
        deletion=DeletionMode.ANONYMIZE_OR_HARD_DELETE,
        days=AI_USAGE_RETENTION_DAYS,
        notes="Usage/cost/latency telemetry only; provider prompt retention is a processor contract.",
    ),
    "user_generated_exports": RetentionRule(
        key="user_generated_exports",
        mode=RetentionMode.NOT_SERVER_PERSISTED,
        deletion=DeletionMode.NOT_APPLICABLE,
        backup_days=None,
        notes="Generated in-memory and streamed to the user; FinCo-Pilot must not persist a server copy.",
    ),
    "production_backups": RetentionRule(
        key="production_backups",
        mode=RetentionMode.ROLLING_DAYS,
        deletion=DeletionMode.HARD_DELETE,
        days=BACKUP_MAX_RETENTION_DAYS,
        backup_days=None,
        notes=(
            "Encrypted production backups expire automatically. A restore must re-apply deletion "
            "tombstones/legal holds before restored data is returned to normal service."
        ),
    ),
}


def get_retention_rule(key: str) -> RetentionRule:
    """Return one canonical rule or fail closed for an unknown category."""

    try:
        return RETENTION_RULES[key]
    except KeyError as exc:
        raise KeyError(f"Unknown retention category: {key}") from exc
