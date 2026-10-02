import json
from pathlib import Path


REGISTRY = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "trust"
    / "processor_inventory.v1.json"
)

REQUIRED_IDS = {
    "zoho_desk",
    "razorpay",
    "pluggy",
    "enable_banking",
    "simplefin",
    "smtp_provider",
    "object_storage",
    "oidc_provider",
    "openexchangerates",
    "yahoo_finance",
    "tesouro_direto",
    "ai_llm_route",
    "hosting_provider",
    "github_private_vulnerability_reporting",
}

ALLOWED_CLASSIFICATIONS = {
    "processor_when_enabled",
    "unresolved_processor",
    "service_vendor_review",
}
ALLOWED_STATUS = {"conditional", "operator_configured", "unresolved"}
ALLOWED_SENSITIVITY = {"low", "moderate", "high", "restricted_financial"}


def _inventory() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def test_processor_inventory_contract_is_complete_and_unique():
    payload = _inventory()

    assert payload["contract"] == "FINCO_THIRD_PARTY_PROCESSOR_INVENTORY_V1"
    assert payload["roadmap_item"] == 12
    assert payload["rules"]["unknown_provider_fails_review"] is True
    assert payload["rules"]["secrets_must_never_be_recorded_here"] is True

    entries = payload["entries"]
    ids = [entry["id"] for entry in entries]

    assert len(ids) == len(set(ids))
    assert REQUIRED_IDS.issubset(set(ids))

    required_fields = {
        "id",
        "service",
        "purpose",
        "classification",
        "status",
        "activation_condition",
        "data_categories",
        "sensitivity",
        "financial_records_expected",
        "deletion_review_required",
        "retention_contract",
        "operator_action_before_activation",
    }

    for entry in entries:
        assert required_fields.issubset(entry)
        assert entry["classification"] in ALLOWED_CLASSIFICATIONS
        assert entry["status"] in ALLOWED_STATUS
        assert entry["sensitivity"] in ALLOWED_SENSITIVITY
        assert entry["data_categories"]
        assert entry["retention_contract"] == "FINCO_DATA_RETENTION_V1"


def test_high_risk_processors_require_deletion_review():
    entries = {entry["id"]: entry for entry in _inventory()["entries"]}

    high_risk_ids = {
        "zoho_desk",
        "razorpay",
        "pluggy",
        "enable_banking",
        "simplefin",
        "smtp_provider",
        "object_storage",
        "oidc_provider",
        "ai_llm_route",
        "hosting_provider",
    }

    for processor_id in high_risk_ids:
        assert entries[processor_id]["deletion_review_required"] is True


def test_unresolved_launch_dependencies_are_not_misrepresented_as_active():
    entries = {entry["id"]: entry for entry in _inventory()["entries"]}

    assert entries["ai_llm_route"]["status"] == "unresolved"
    assert entries["ai_llm_route"]["classification"] == "unresolved_processor"
    assert entries["hosting_provider"]["status"] == "unresolved"
    assert entries["hosting_provider"]["classification"] == "unresolved_processor"


def test_inventory_contains_no_secret_value_fields():
    payload = _inventory()

    forbidden_field_names = {
        "secret",
        "password",
        "api_key",
        "access_token",
        "refresh_token",
        "client_secret",
        "private_key",
        "credential",
        "credential_value",
    }

    def walk(value):
        if isinstance(value, dict):
            for key, nested in value.items():
                assert key.lower() not in forbidden_field_names
                walk(nested)
        elif isinstance(value, list):
            for nested in value:
                walk(nested)

    walk(payload)
