"""Canonical third-party recipient / processor inventory for FinCo-Pilot.

Roadmap #12 is intentionally a data-flow inventory, not a blanket legal-role
declaration.  A vendor can be a processor, independent fiduciary/controller,
regulated intermediary, or a mixed role depending on the service and contract.
The registry therefore records the technical boundary and requires explicit
contract review instead of guessing the legal classification.

This module does not enable any integration.  It exists so later production
configuration, privacy copy, deletion orchestration and vendor acceptance can
consume one reviewed source of truth.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


INVENTORY_ID = "FINCO_THIRD_PARTY_PROCESSOR_INVENTORY_V1"
INVENTORY_VERSION = "2026-10-03"


class BoundaryStatus(str, Enum):
    SELECTED_RELEASE_GATED = "selected_release_gated"
    OPTIONAL_RELEASE_GATED = "optional_release_gated"
    UNRESOLVED = "unresolved"
    USER_DIRECTED = "user_directed"
    INTERNAL_SELF_HOSTED = "internal_self_hosted"
    NO_PERSONAL_DATA_BY_DESIGN = "no_personal_data_by_design"


class LegalRoleStatus(str, Enum):
    CONTRACT_REVIEW_REQUIRED = "contract_review_required"
    NOT_APPLICABLE_INTERNAL = "not_applicable_internal"
    NOT_A_PERSONAL_DATA_RECIPIENT_BY_DESIGN = "not_a_personal_data_recipient_by_design"


class DeletionExpectation(str, Enum):
    PROVIDER_DELETE = "provider_delete"
    REVOKE_THEN_DELETE = "revoke_then_delete"
    CONTRACTUAL_RETENTION_THEN_DELETE = "contractual_retention_then_delete"
    USER_DIRECTED_PROVIDER = "user_directed_provider"
    OPERATOR_INFRA_LIFECYCLE = "operator_infra_lifecycle"
    NOT_APPLICABLE = "not_applicable"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class ThirdPartyBoundary:
    key: str
    service: str
    status: BoundaryStatus
    purpose: str
    data_classes: tuple[str, ...]
    sends_personal_data: bool
    sends_financial_data: bool
    sends_secrets_or_credentials: bool
    legal_role: LegalRoleStatus
    deletion: DeletionExpectation
    roadmap_gates: tuple[int, ...]
    public_docs: tuple[str, ...] = ()
    notes: str = ""

    @property
    def is_external(self) -> bool:
        return self.status is not BoundaryStatus.INTERNAL_SELF_HOSTED

    @property
    def is_operator_selected(self) -> bool:
        return self.status is BoundaryStatus.SELECTED_RELEASE_GATED

    @property
    def production_is_release_gated(self) -> bool:
        return self.status in {
            BoundaryStatus.SELECTED_RELEASE_GATED,
            BoundaryStatus.OPTIONAL_RELEASE_GATED,
            BoundaryStatus.UNRESOLVED,
        }


THIRD_PARTY_BOUNDARIES: dict[str, ThirdPartyBoundary] = {
    "zoho_desk": ThirdPartyBoundary(
        key="zoho_desk",
        service="Zoho Desk",
        status=BoundaryStatus.SELECTED_RELEASE_GATED,
        purpose="customer support ticket intake, replies, and support-case administration",
        data_classes=("support_contact", "ticket_content", "safe_diagnostics", "request_reference"),
        sends_personal_data=True,
        sends_financial_data=False,
        sends_secrets_or_credentials=False,
        legal_role=LegalRoleStatus.CONTRACT_REVIEW_REQUIRED,
        deletion=DeletionExpectation.PROVIDER_DELETE,
        roadmap_gates=(7, 12, 27, 29),
        public_docs=(
            "https://help.zoho.com/portal/en/kb/desk/user-management-and-security/"
            "data-security/articles/data-retention",
            "https://help.zoho.com/portal/en/kb/desk/data-administration/recycle-bin/"
            "articles/using-the-recycle-bin",
        ),
        notes=(
            "Selected support system. Direct FinCo-Pilot-to-Zoho acceptance and replacement "
            "of the previously exposed OAuth credential remain release gates. Normal support "
            "must never auto-attach raw balances, transactions, passwords, tokens, or secrets."
        ),
    ),
    "razorpay": ThirdPartyBoundary(
        key="razorpay",
        service="Razorpay Payments",
        status=BoundaryStatus.SELECTED_RELEASE_GATED,
        purpose=(
            "payment order, checkout, payment verification, subscriptions, refunds, "
            "and billing evidence"
        ),
        data_classes=(
            "customer_contact",
            "order_and_payment_identifiers",
            "amount_currency",
            "subscription_state",
            "merchant_kyc_outside_app",
        ),
        sends_personal_data=True,
        sends_financial_data=True,
        sends_secrets_or_credentials=False,
        legal_role=LegalRoleStatus.CONTRACT_REVIEW_REQUIRED,
        deletion=DeletionExpectation.CONTRACTUAL_RETENTION_THEN_DELETE,
        roadmap_gates=(3, 4, 12, 31, 32, 33, 34, 35, 36, 37, 38, 39),
        public_docs=(
            "https://razorpay.com/terms/",
            "https://razorpay.com/buyer-privacy-notice/",
        ),
        notes=(
            "Selected payment provider. FinCo-Pilot must not persist full PAN/CVV/CVC. "
            "Production activation still requires current merchant-contract, retention, "
            "refund/cancellation, tax/accounting and provider-deletion review."
        ),
    ),
    "pluggy": ThirdPartyBoundary(
        key="pluggy",
        service="Pluggy",
        status=BoundaryStatus.OPTIONAL_RELEASE_GATED,
        purpose="optional bank/open-finance connection and financial-data synchronization",
        data_classes=(
            "bank_connection_consent",
            "provider_tokens",
            "account_identity",
            "balances",
            "transactions",
            "cards_loans_investments",
        ),
        sends_personal_data=True,
        sends_financial_data=True,
        sends_secrets_or_credentials=True,
        legal_role=LegalRoleStatus.CONTRACT_REVIEW_REQUIRED,
        deletion=DeletionExpectation.REVOKE_THEN_DELETE,
        roadmap_gates=(12, 46),
        public_docs=(
            "https://www.pluggy.ai/legal",
            "https://docs.pluggy.ai/en",
        ),
        notes=(
            "Optional existing connector, not an Indian AA/FIU substitute. Production use "
            "requires current contract/privacy/retention review plus live revoke/delete "
            "acceptance against the actual provider account."
        ),
    ),
    "enable_banking": ThirdPartyBoundary(
        key="enable_banking",
        service="Enable Banking",
        status=BoundaryStatus.OPTIONAL_RELEASE_GATED,
        purpose="optional PSD2/open-banking connection and account-information synchronization",
        data_classes=(
            "bank_consent",
            "account_identity",
            "balances",
            "transactions",
            "provider_session_identifiers",
        ),
        sends_personal_data=True,
        sends_financial_data=True,
        sends_secrets_or_credentials=True,
        legal_role=LegalRoleStatus.CONTRACT_REVIEW_REQUIRED,
        deletion=DeletionExpectation.REVOKE_THEN_DELETE,
        roadmap_gates=(12, 46, 47),
        public_docs=("https://enablebanking.com/privacy/",),
        notes=(
            "Optional existing connector. The public website/control-panel privacy notice does "
            "not by itself establish the retention/deletion contract for end-user banking API "
            "data, so production use remains gated on service-specific contract verification."
        ),
    ),
    "simplefin": ThirdPartyBoundary(
        key="simplefin",
        service="SimpleFIN / selected SimpleFIN server",
        status=BoundaryStatus.OPTIONAL_RELEASE_GATED,
        purpose="optional read-only financial account and transaction synchronization",
        data_classes=("access_url_token", "account_identity", "balances", "transactions"),
        sends_personal_data=True,
        sends_financial_data=True,
        sends_secrets_or_credentials=True,
        legal_role=LegalRoleStatus.CONTRACT_REVIEW_REQUIRED,
        deletion=DeletionExpectation.REVOKE_THEN_DELETE,
        roadmap_gates=(12, 46, 48),
        public_docs=(
            "https://beta-bridge.simplefin.org/info/privacy",
            "https://www.simplefin.org/",
        ),
        notes=(
            "The actual data recipient depends on the SimpleFIN server/bridge chosen by the "
            "user. Inventory and deletion acceptance must bind to that concrete server rather "
            "than treating 'SimpleFIN' as one universal processor."
        ),
    ),
    "omniroute": ThirdPartyBoundary(
        key="omniroute",
        service="OmniRoute",
        status=BoundaryStatus.INTERNAL_SELF_HOSTED,
        purpose="operator-controlled AI routing/control boundary",
        data_classes=("ai_request_envelope", "model_route_metadata"),
        sends_personal_data=False,
        sends_financial_data=False,
        sends_secrets_or_credentials=False,
        legal_role=LegalRoleStatus.NOT_APPLICABLE_INTERNAL,
        deletion=DeletionExpectation.OPERATOR_INFRA_LIFECYCLE,
        roadmap_gates=(6, 12, 49, 50),
        notes=(
            "OmniRoute itself is treated as internal only when operator-hosted. The external "
            "model/search provider selected behind it is a separate third-party recipient and "
            "must be explicitly approved below before production Core Copilot traffic."
        ),
    ),
    "operator_ai_upstream": ThirdPartyBoundary(
        key="operator_ai_upstream",
        service="Production Core Copilot upstream model/search provider",
        status=BoundaryStatus.UNRESOLVED,
        purpose="model inference and any explicitly approved supporting AI/search calls",
        data_classes=(
            "user_prompt",
            "authorised_page_context",
            "tool_results",
            "rag_context",
            "potential_financial_context",
        ),
        sends_personal_data=True,
        sends_financial_data=True,
        sends_secrets_or_credentials=False,
        legal_role=LegalRoleStatus.CONTRACT_REVIEW_REQUIRED,
        deletion=DeletionExpectation.UNRESOLVED,
        roadmap_gates=(6, 12, 49, 50),
        notes=(
            "No production upstream is approved by this inventory. OpenRouter/NVIDIA/Ollama "
            "Cloud/other locally configured OmniRoute candidates remain candidates only until "
            "vendor-specific retention, training, residency, DPA, cost and failure behavior are "
            "accepted. Core Copilot must fail safely rather than route to an unapproved target."
        ),
    ),
    "user_configured_llm": ThirdPartyBoundary(
        key="user_configured_llm",
        service="User-configured Advanced Agent LLM endpoint",
        status=BoundaryStatus.USER_DIRECTED,
        purpose="explicit user-configured custom/Advanced Agent inference",
        data_classes=("agent_prompt", "tool_results", "rag_context", "user_selected_context"),
        sends_personal_data=True,
        sends_financial_data=True,
        sends_secrets_or_credentials=False,
        legal_role=LegalRoleStatus.CONTRACT_REVIEW_REQUIRED,
        deletion=DeletionExpectation.USER_DIRECTED_PROVIDER,
        roadmap_gates=(12, 50),
        notes=(
            "This is not an operator-approved Core Copilot subprocessor. The user chooses the "
            "endpoint/connection. Product disclosure and scope controls must keep it separate "
            "from the system-managed Core Copilot route."
        ),
    ),
    "external_mcp_servers": ThirdPartyBoundary(
        key="external_mcp_servers",
        service="User/operator-configured external MCP servers",
        status=BoundaryStatus.USER_DIRECTED,
        purpose="explicit external tool/resource integrations for Advanced Agents",
        data_classes=("tool_arguments", "tool_results", "user_selected_context"),
        sends_personal_data=True,
        sends_financial_data=True,
        sends_secrets_or_credentials=False,
        legal_role=LegalRoleStatus.CONTRACT_REVIEW_REQUIRED,
        deletion=DeletionExpectation.USER_DIRECTED_PROVIDER,
        roadmap_gates=(12, 50, 51),
        notes=(
            "Unknown MCP tools are hidden from Core Copilot by default. External MCP is a "
            "separate explicit integration boundary and must not become a silent Core route."
        ),
    ),
    "smtp_provider": ThirdPartyBoundary(
        key="smtp_provider",
        service="Transactional SMTP/email provider",
        status=BoundaryStatus.UNRESOLVED,
        purpose="verification, password reset, security and transactional email delivery",
        data_classes=("email_address", "transactional_message", "short_lived_authentication_link", "delivery_metadata"),
        sends_personal_data=True,
        sends_financial_data=False,
        sends_secrets_or_credentials=True,
        legal_role=LegalRoleStatus.CONTRACT_REVIEW_REQUIRED,
        deletion=DeletionExpectation.UNRESOLVED,
        roadmap_gates=(12, 17, 23, 24, 27),
        notes=("Brevo is the researched #17 zero-cost recommendation, not an activated/approved "
               "production processor. SMTP receives short-lived reset/verification links, not "
               "SMTP credentials or financial records. Retention/residency/deletion and live "
               "delivery remain acceptance gates; see FINCO_PRODUCTION_SMTP_V1.md."),
    ),
    "object_storage_provider": ThirdPartyBoundary(
        key="object_storage_provider",
        service="Cloudflare R2",
        status=BoundaryStatus.SELECTED_RELEASE_GATED,
        purpose="transaction attachments, invoice/logo objects, and other production file bytes",
        data_classes=("uploaded_files", "document_metadata"),
        sends_personal_data=True,
        sends_financial_data=True,
        sends_secrets_or_credentials=False,
        legal_role=LegalRoleStatus.CONTRACT_REVIEW_REQUIRED,
        deletion=DeletionExpectation.OPERATOR_INFRA_LIFECYCLE,
        roadmap_gates=(12, 16, 25, 29, 30),
        public_docs=(
            "https://developers.cloudflare.com/r2/api/s3/",
            "https://developers.cloudflare.com/r2/reference/data-security/",
            "https://developers.cloudflare.com/r2/reference/data-location/",
        ),
        notes=(
            "Selected for the zero-cost roadmap #16 path through R2's private S3-compatible "
            "API. Production remains release-gated until the operator-owned bucket, scoped "
            "Object Read & Write credentials, endpoint/region, upload-read-delete acceptance "
            "probe and provider/data-location review are verified. R2 location hints are not "
            "an India-residency guarantee, and roadmap #25 still owns isolated restore proof."
        ),
    ),
    "cloudflare_edge": ThirdPartyBoundary(
        key="cloudflare_edge",
        service="Cloudflare DNS / TLS edge / Tunnel",
        status=BoundaryStatus.SELECTED_RELEASE_GATED,
        purpose="public DNS, TLS edge termination, DDoS/security edge, and private tunnel transport to the FinCo-Pilot origin",
        data_classes=(
            "ip_address",
            "http_request_metadata",
            "http_headers",
            "request_response_content_in_transit",
            "authentication_session_headers_in_transit",
        ),
        sends_personal_data=True,
        sends_financial_data=True,
        sends_secrets_or_credentials=True,
        legal_role=LegalRoleStatus.CONTRACT_REVIEW_REQUIRED,
        deletion=DeletionExpectation.CONTRACTUAL_RETENTION_THEN_DELETE,
        roadmap_gates=(1, 2, 12, 25, 26, 58),
        public_docs=(
            "https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/",
            "https://www.cloudflare.com/privacypolicy/",
            "https://developers.cloudflare.com/data-localization/",
        ),
        notes=(
            "Selected zero-cost edge path. An operator-owned remotely managed Tunnel and "
            "dedicated FinCo-Pilot hostname are provisioned without changing the existing "
            "root-site/mail records. Production remains release-gated until a durable origin "
            "connector, edge-cache/security rules, retention/contract review, and live HTTPS/API "
            "acceptance pass. Cloudflare edge selection does not select the compute host/log sink."
        ),
    ),
    "hosting_logging_provider": ThirdPartyBoundary(
        key="hosting_logging_provider",
        service="Production compute host / application log sink",
        status=BoundaryStatus.UNRESOLVED,
        purpose="serve FinCo-Pilot and retain bounded security/request logs",
        data_classes=("ip_address", "request_metadata", "request_reference", "security_logs"),
        sends_personal_data=True,
        sends_financial_data=False,
        sends_secrets_or_credentials=False,
        legal_role=LegalRoleStatus.CONTRACT_REVIEW_REQUIRED,
        deletion=DeletionExpectation.OPERATOR_INFRA_LIFECYCLE,
        roadmap_gates=(1, 2, 12, 25, 26, 58),
        notes=(
            "No production compute/log vendor is selected. Cloudflare edge is tracked separately. "
            "India residency and automatic log "
            "expiry cannot be claimed until the actual deployment is configured and verified."
        ),
    ),
    "managed_postgresql": ThirdPartyBoundary(
        key="managed_postgresql",
        service="Neon Postgres",
        status=BoundaryStatus.SELECTED_RELEASE_GATED,
        purpose="primary relational database hosting",
        data_classes=("all_primary_application_records",),
        sends_personal_data=True,
        sends_financial_data=True,
        sends_secrets_or_credentials=True,
        legal_role=LegalRoleStatus.CONTRACT_REVIEW_REQUIRED,
        deletion=DeletionExpectation.OPERATOR_INFRA_LIFECYCLE,
        roadmap_gates=(12, 14, 25, 26),
        public_docs=(
            "https://neon.com/security",
            "https://neon.com/docs/security/security-overview",
        ),
        notes=(
            "Selected for the zero-cost roadmap #14 production PostgreSQL path. "
            "The actual Neon project, region, direct endpoint, secret-managed DATABASE_URL, "
            "migration run and live acceptance probe remain release gates. Provider history "
            "or PITR does not replace roadmap #25's isolated restore rehearsal."
        ),
    ),
    "managed_redis": ThirdPartyBoundary(
        key="managed_redis",
        service="External Redis provider if managed hosting is chosen",
        status=BoundaryStatus.UNRESOLVED,
        purpose="queues, rate limits, OAuth/auth challenges and ephemeral operational state",
        data_classes=("ephemeral_auth_state", "rate_limit_state", "job_payloads"),
        sends_personal_data=True,
        sends_financial_data=False,
        sends_secrets_or_credentials=True,
        legal_role=LegalRoleStatus.CONTRACT_REVIEW_REQUIRED,
        deletion=DeletionExpectation.OPERATOR_INFRA_LIFECYCLE,
        roadmap_gates=(12, 15, 25, 26),
        notes=(
            "Not a third party when self-hosted; ephemeral state must retain explicit TTLs "
            "and stay out of backups."
        ),
    ),
    "oidc_provider": ThirdPartyBoundary(
        key="oidc_provider",
        service="Optional configured OIDC identity provider",
        status=BoundaryStatus.UNRESOLVED,
        purpose="optional federated authentication",
        data_classes=("identity_subject", "email", "oidc_claims", "login_metadata"),
        sends_personal_data=True,
        sends_financial_data=False,
        sends_secrets_or_credentials=False,
        legal_role=LegalRoleStatus.CONTRACT_REVIEW_REQUIRED,
        deletion=DeletionExpectation.UNRESOLVED,
        roadmap_gates=(12, 27),
        notes=(
            "No production OIDC provider is selected; local authentication can operate "
            "without this boundary."
        ),
    ),
    "yahoo_finance": ThirdPartyBoundary(
        key="yahoo_finance",
        service="Yahoo Finance via yfinance",
        status=BoundaryStatus.NO_PERSONAL_DATA_BY_DESIGN,
        purpose="market symbol search and reference-price lookup",
        data_classes=("ticker_or_symbol_query", "network_metadata"),
        sends_personal_data=False,
        sends_financial_data=False,
        sends_secrets_or_credentials=False,
        legal_role=LegalRoleStatus.NOT_A_PERSONAL_DATA_RECIPIENT_BY_DESIGN,
        deletion=DeletionExpectation.NOT_APPLICABLE,
        roadmap_gates=(12, 27),
        notes=(
            "Application requests market symbols/reference prices rather than user identity, "
            "account IDs, portfolio quantities or transaction records. Symbol queries can still "
            "reveal investment interests, so provider terms/privacy must remain under review."
        ),
    ),
    "tesouro_direto": ThirdPartyBoundary(
        key="tesouro_direto",
        service="Tesouro Direto public market-data source",
        status=BoundaryStatus.NO_PERSONAL_DATA_BY_DESIGN,
        purpose="Brazilian Treasury bond reference-price lookup",
        data_classes=("public_bond_reference_query", "network_metadata"),
        sends_personal_data=False,
        sends_financial_data=False,
        sends_secrets_or_credentials=False,
        legal_role=LegalRoleStatus.NOT_A_PERSONAL_DATA_RECIPIENT_BY_DESIGN,
        deletion=DeletionExpectation.NOT_APPLICABLE,
        roadmap_gates=(12, 27),
        notes=(
            "Keep requests limited to public reference data. If future code sends user, "
            "portfolio or transaction context, this boundary must be reclassified first."
        ),
    ),
    "github_private_vulnerability_reporting": ThirdPartyBoundary(
        key="github_private_vulnerability_reporting",
        service="GitHub Private Vulnerability Reporting",
        status=BoundaryStatus.USER_DIRECTED,
        purpose="receive security vulnerability reports separately from customer support",
        data_classes=("reporter_identity", "security_report_content", "technical_reproduction_details"),
        sends_personal_data=True,
        sends_financial_data=False,
        sends_secrets_or_credentials=False,
        legal_role=LegalRoleStatus.CONTRACT_REVIEW_REQUIRED,
        deletion=DeletionExpectation.USER_DIRECTED_PROVIDER,
        roadmap_gates=(7, 12, 27),
        notes=(
            "Security reporting is separate from the customer-support queue. Reporters must "
            "not be asked for unnecessary user financial records or authentication secrets."
        ),
    ),
    "open_exchange_rates": ThirdPartyBoundary(
        key="open_exchange_rates",
        service="Open Exchange Rates",
        status=BoundaryStatus.NO_PERSONAL_DATA_BY_DESIGN,
        purpose="public/reference foreign-exchange rates",
        data_classes=("requested_currency_symbols", "network_metadata"),
        sends_personal_data=False,
        sends_financial_data=False,
        sends_secrets_or_credentials=False,
        legal_role=LegalRoleStatus.NOT_A_PERSONAL_DATA_RECIPIENT_BY_DESIGN,
        deletion=DeletionExpectation.NOT_APPLICABLE,
        roadmap_gates=(12, 18),
        public_docs=("https://openexchangerates.org/privacy",),
        notes=(
            "Application requests rate symbols, not user/account/transaction data. If future "
            "code adds user-specific query data, this classification must be re-reviewed."
        ),
    ),
}


def get_third_party_boundary(key: str) -> ThirdPartyBoundary:
    try:
        return THIRD_PARTY_BOUNDARIES[key]
    except KeyError as exc:
        raise KeyError(f"Unknown third-party boundary: {key}") from exc


def unresolved_operator_boundaries() -> tuple[ThirdPartyBoundary, ...]:
    """Return operator-controlled external boundaries that still need a vendor/gate."""

    return tuple(
        boundary
        for boundary in THIRD_PARTY_BOUNDARIES.values()
        if boundary.status
        in {
            BoundaryStatus.SELECTED_RELEASE_GATED,
            BoundaryStatus.OPTIONAL_RELEASE_GATED,
            BoundaryStatus.UNRESOLVED,
        }
    )
