from datetime import date, timedelta
import json

import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.core.privacy_policy import VERSION, publication_blockers, public_policy


def ready():
    return dict(
        operator_legal_name="Synthetic operator",
        privacy_contact_name="Privacy officer",
        privacy_contact_email="privacy@example.com",
        privacy_contact_address="Synthetic public office",
        privacy_processing_locations="Synthetic location",
        privacy_infrastructure_providers="Synthetic providers",
        privacy_policy_reviewed_version=VERSION,
        privacy_policy_effective_date=date.today().isoformat(),
    )


def test_default_is_draft_and_never_invents_contact_or_effective_date():
    settings = Settings(_env_file=None)
    policy = public_policy(settings)
    assert policy["status"] == "draft"
    assert policy["effective_date"] is None
    assert policy["contact"] == dict(name=None, email=None, address=None)
    assert "privacy_contact_email" in publication_blockers(settings)


@pytest.mark.parametrize("key", list(ready()))
def test_publication_rejects_each_missing_fact(key):
    values = ready()
    values[key] = ""
    with pytest.raises(ValidationError):
        Settings(_env_file=None, privacy_policy_published=True, **values)


@pytest.mark.parametrize(
    "override",
    [
        {"privacy_policy_reviewed_version": "obsolete"},
        {"privacy_policy_effective_date": (date.today() + timedelta(days=1)).isoformat()},
        {"privacy_policy_effective_date": "not-a-date"},
        {"operator_identity_enabled": False},
        {"operator_country_code": "US"},
        {"privacy_contact_email": "x\r\nBcc: stolen@example.com"},
        {"privacy_contact_address": "hidden\nsecond line"},
        {"privacy_processing_locations": "https://user:secret@example.com"},
        {"privacy_infrastructure_providers": "x" * 501},
    ],
)
def test_invalid_publication_is_fail_closed(override):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, privacy_policy_published=True, **(ready() | override))


def test_complete_explicit_review_can_publish_and_never_exposes_secrets():
    settings = Settings(
        _env_file=None,
        privacy_policy_published=True,
        secret_key="synthetic-private-canary",
        **ready(),
    )
    policy = public_policy(settings)
    assert policy["status"] == "published"
    assert policy["effective_date"] == date.today().isoformat()
    assert "synthetic-private-canary" not in json.dumps(policy)
    assert len({s["id"] for s in policy["sections"]}) == 12
    assert all(
        s[field][lang]
        for s in policy["sections"]
        for field in ("title", "body")
        for lang in ("en", "hi")
    )
    settings.privacy_contact_email = ""
    assert public_policy(settings)["status"] == "draft"


def test_disabled_operator_identity_is_not_publicly_exposed():
    settings = Settings(
        _env_file=None, operator_identity_enabled=False, operator_legal_name="Private canary"
    )
    assert public_policy(settings)["operator"]["legal_name"] is None


@pytest.mark.asyncio
async def test_logged_out_endpoint_is_public_noncacheable_and_has_no_settings_dump(client):
    response = await client.get("/api/privacy-policy")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["version"] == VERSION
    assert get_settings().secret_key.get_secret_value() not in response.text
    assert "publication_blockers" not in response.json()


def test_operator_checker_reports_missing_codes_without_private_values(monkeypatch, capsys):
    from scripts import verify_privacy_publication
    settings = Settings(_env_file=None, secret_key="synthetic-private-canary")
    monkeypatch.setattr(verify_privacy_publication, "get_settings", lambda: settings)
    assert verify_privacy_publication.main() == 1
    output = capsys.readouterr().out
    assert "privacy_contact_email" in output
    assert "synthetic-private-canary" not in output


def test_operator_checker_accepts_complete_declarations_without_claiming_live_proof(monkeypatch, capsys):
    from scripts import verify_privacy_publication
    settings = Settings(_env_file=None, privacy_policy_published=True, **ready())
    monkeypatch.setattr(verify_privacy_publication, "get_settings", lambda: settings)
    assert verify_privacy_publication.main() == 0
    assert "verify the live URL" in capsys.readouterr().out
