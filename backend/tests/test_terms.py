from datetime import date, timedelta
import json
import subprocess
import sys

import pytest
from pydantic import ValidationError

from app.billing.pricing import PRICE_CATALOG
from app.core.config import Settings, get_settings
from app.core.privacy_policy import VERSION as PRIVACY_VERSION
from app.core.terms import CONTACT_FIELDS, COMMERCIAL_FIELDS, VERSION, public_terms


def ready():
    return {
        "operator_legal_name": "Synthetic operator",
        "privacy_policy_published": True,
        "privacy_policy_reviewed_version": PRIVACY_VERSION,
        "privacy_policy_effective_date": date.today().isoformat(),
        "privacy_contact_name": "Synthetic officer",
        "privacy_contact_email": "privacy@example.com",
        "privacy_contact_address": "Synthetic office",
        "privacy_processing_locations": "Synthetic location",
        "privacy_infrastructure_providers": "Synthetic providers",
        "terms_contact_name": "Synthetic officer",
        "terms_contact_email": "terms@example.com",
        "terms_contact_address": "Synthetic office",
        "terms_contact_phone": "+91 0000000000",
        "terms_contact_designation": "Grievance contact",
        "terms_public_website": "https://example.com",
        "terms_reviewed_version": VERSION,
        "terms_effective_date": date.today().isoformat(),
        **{key: "Synthetic reviewed decision" for key in COMMERCIAL_FIELDS},
    }


def test_settings_and_publication_checker_bootstrap_without_orm_import_cycle():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from app.core.config import Settings; Settings(_env_file=None); from app.core.database import Base; from scripts.verify_terms_publication import main; raise SystemExit(main())",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 1
    assert "Publication blocked:" in result.stdout
    assert "ImportError" not in result.stderr


def test_default_terms_are_draft_with_no_invented_identity_or_contract():
    terms = public_terms(Settings(_env_file=None))
    assert terms["status"] == "draft"
    assert terms["effective_date"] is None
    assert not any(terms["contact"].values())
    assert terms["operator"]["legal_name"] is None
    assert all(value is None for value in terms["commercial"]["refund_policy"].values())


@pytest.mark.parametrize(
    "key",
    [
        "operator_legal_name",
        *CONTACT_FIELDS,
        *COMMERCIAL_FIELDS,
        "terms_reviewed_version",
        "terms_effective_date",
    ],
)
def test_each_missing_fact_prevents_publication(key):
    values = ready() | {key: ""}
    with pytest.raises(ValidationError):
        Settings(_env_file=None, terms_published=True, **values)


@pytest.mark.parametrize(
    "override",
    [
        {"terms_reviewed_version": "obsolete"},
        {"terms_effective_date": (date.today() + timedelta(days=1)).isoformat()},
        {"terms_effective_date": "invalid"},
        {"operator_identity_enabled": False},
        {"operator_country_code": "US"},
        {"privacy_policy_published": False},
        {"billing_checkout_enabled": True},
        {"terms_contact_email": "x\r\nBcc: leak@example.com"},
        {"terms_contact_phone": "not a phone"},
        {"terms_contact_address": "first\nsecond"},
        {"terms_refund_policy_en": "x" * 2001},
        {"terms_public_website": "http://example.com"},
        {"terms_public_website": "https://user:password@example.com"},
        {"terms_public_website": "https://example.com?token=private"},
        {"terms_public_website": "https://example.com#private"},
    ],
)
def test_invalid_stale_or_unfinished_publication_fails_closed(override):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, terms_published=True, **(ready() | override))


def test_complete_review_is_publishable_but_not_proof_of_paid_lifecycle():
    settings = Settings(
        _env_file=None, terms_published=True, secret_key="synthetic-private-canary", **ready()
    )
    terms = public_terms(settings)
    assert terms["status"] == "published"
    assert terms["effective_date"] == date.today().isoformat()
    assert "synthetic-private-canary" not in json.dumps(terms)
    for capability in (
        "live_payments",
        "automatic_paid_activation",
        "recurring_billing",
        "automated_refunds",
    ):
        assert terms["commercial"][capability] is False
    assert [p["amount_minor"] for p in terms["commercial"]["prices"]] == [
        p.amount_minor for p in PRICE_CATALOG.values()
    ]
    assert len({s["id"] for s in terms["sections"]}) == 12
    assert all(
        s[key][lang]
        for s in terms["sections"]
        for key in ("title", "body")
        for lang in ("en", "hi")
    )
    settings.privacy_policy_published = False
    assert public_terms(settings)["status"] == "draft"


def test_disabled_identity_and_lost_contact_are_fail_closed():
    settings = Settings(
        _env_file=None, operator_identity_enabled=False, operator_legal_name="Private canary"
    )
    assert public_terms(settings)["operator"]["legal_name"] is None
    settings = Settings(_env_file=None, terms_published=True, **ready())
    settings.terms_contact_email = ""
    assert public_terms(settings)["status"] == "draft"


@pytest.mark.asyncio
async def test_logged_out_terms_api_has_no_workspace_or_secret_payload(client):
    response = await client.get("/api/terms")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["version"] == VERSION
    assert get_settings().secret_key.get_secret_value() not in response.text
    assert set(response.json()) == {
        "version",
        "reviewed_on",
        "status",
        "effective_date",
        "operator",
        "contact",
        "commercial",
        "sections",
    }


@pytest.mark.parametrize("published", [False, True])
def test_operator_checker_does_not_print_private_fields(monkeypatch, capsys, published):
    from scripts import verify_terms_publication

    settings = Settings(
        _env_file=None,
        terms_published=published,
        secret_key="synthetic-private-canary",
        **(ready() if published else {}),
    )
    monkeypatch.setattr(verify_terms_publication, "get_settings", lambda: settings)
    assert verify_terms_publication.main() == (0 if published else 1)
    output = capsys.readouterr().out
    assert "synthetic-private-canary" not in output
    assert "terms@example.com" not in output
    if published:
        assert "acceptance separately" in output
