from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class SupportCategory(StrEnum):
    ACCOUNT_ACCESS = "account_access"
    BILLING_PAYMENT = "billing_payment"
    BANK_CONNECTION = "bank_connection"
    TRANSACTIONS_IMPORT = "transactions_import"
    SAFE_TO_SPEND = "safe_to_spend"
    FINCO_COPILOT = "finco_copilot"
    BUG_PERFORMANCE = "bug_performance"
    PRIVACY_DATA = "privacy_data"
    FEATURE_REQUEST = "feature_request"
    OTHER = "other"


class SupportTicketCreate(BaseModel):
    category: SupportCategory
    subject: str = Field(min_length=4, max_length=160)
    message: str = Field(min_length=10, max_length=5000)
    page_path: str | None = Field(default=None, max_length=500)
    app_version: str | None = Field(default=None, max_length=80)
    locale: str | None = Field(default=None, max_length=32)
    error_reference: str | None = Field(default=None, max_length=64)

    @field_validator("subject")
    @classmethod
    def normalize_subject(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 4:
            raise ValueError("subject is too short")
        return value

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 10:
            raise ValueError("message is too short")
        return value

    @field_validator("page_path")
    @classmethod
    def validate_page_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        # Diagnostics only need an app-relative path. Reject full URLs so query
        # strings cannot accidentally forward OAuth codes or other secrets.
        if not value.startswith("/") or "://" in value:
            raise ValueError("page_path must be an app-relative path")
        return value.split("?", 1)[0].split("#", 1)[0][:500]


class SupportTicketRead(BaseModel):
    reference: str
    ticket_id: str
    ticket_number: str | None = None
    support_tier: str
    priority: str


class SupportPublicInfo(BaseModel):
    enabled: bool
    email: str | None = None
    portal_url: str | None = None
    help_center_url: str | None = None
    security_url: str | None = None
    direct_ticket_submission: bool = False
    categories: list[str] = Field(default_factory=list)
