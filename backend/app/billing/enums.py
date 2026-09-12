from enum import StrEnum


class PlanId(StrEnum):
    FREE = "free"
    PRO = "pro"
    MAX = "max"


class SubscriptionStatus(StrEnum):
    FREE = "free"
    ACTIVE = "active"
    GRACE = "grace"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    EXPIRED = "expired"


class BillingInterval(StrEnum):
    NONE = "none"
    MONTHLY = "monthly"
    ANNUAL = "annual"


class Capability(StrEnum):
    ADVANCED_REPORTS = "advanced_reports"
    RULES = "rules"
    SMART_RECONCILIATION = "smart_reconciliation"
    BUSINESS_WORKSPACES = "business_workspaces"
    INVOICES = "invoices"
    AGENTS_AUTOMATION = "agents_automation"


class Metric(StrEnum):
    TOTAL_WORKSPACES = "total_workspaces"
    PERSONAL_WORKSPACES = "personal_workspaces"
    BUSINESS_WORKSPACES = "business_workspaces"
    ACCOUNTS = "accounts"
    ACTIVE_BUDGETS = "active_budgets"
    ACTIVE_GOALS = "active_goals"
    ACTIVE_RECURRING = "active_recurring"
    ASSETS = "assets"
    IMPORTS_MONTHLY = "imports_monthly"
    RULES = "rules"
    ACTIVE_SPLIT_GROUPS = "active_split_groups"
    GROUP_MEMBERS = "group_members"
    INVOICES_MONTHLY = "invoices_monthly"
    AI_ACTIONS_MONTHLY = "ai_actions_monthly"
    STORAGE_BYTES = "storage_bytes"
