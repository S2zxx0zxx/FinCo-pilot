"""Sentry event data-minimization acceptance (no external Sentry traffic)."""
from app.core.sentry_monitoring import sanitize_event


def test_sensitive_data_scrubbed():
    event = {
        "request": {"url": "https://example.test/i/secret?token=private", "data": {"iban": "private"}},
        "user": {"id": "user-123", "email": "private@example.test"},
        "contexts": {"custom": {"account": "private"}},
        "breadcrumbs": [{"message": "credit card 4111"}],
        "tags": {"workspace": "secret-workspace"},
        "extra": {"balance": "8000"},
        "message": "private debt",
        "logentry": {"message": "private debt"},
        "transaction": "/api/accounts/user-123",
        "exception": {"values": [{"type": "ValueError", "value": "account number 4111", "stacktrace": {
            "frames": [{"filename": "app/api/accounts.py", "lineno": 29, "function": "get_account",
                        "vars": {"secret": "hidden"}, "context_line": "secret = 3",
                        "pre_context": ["private"], "post_context": ["private"],
                        "abs_path": "/home/private/app/api/accounts.py"}]
        }}]},
    }
    result = sanitize_event(event, "api")
    raw = repr(result)
    for private in ("user-123", "4111", "8000", "private", "secret-workspace"):
        assert private not in raw
    frame = result["exception"]["values"][0]["stacktrace"]["frames"][0]
    assert frame == {"filename": "app/api/accounts.py", "lineno": 29, "function": "get_account"}
    assert result["exception"]["values"][0]["type"] == "ValueError"
    assert result["tags"] == {"component": "api"}


def test_missing_dsn_does_not_initialize(monkeypatch):
    from app.core import sentry_monitoring
    monkeypatch.setattr(sentry_monitoring, "_INITIALIZED", False)
    monkeypatch.setenv("SENTRY_ENABLED", "true")
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    assert not sentry_monitoring.init_sentry()


def test_opt_in_required_even_if_dsn_present(monkeypatch):
    from app.core import sentry_monitoring
    monkeypatch.setattr(sentry_monitoring, "_INITIALIZED", False)
    monkeypatch.delenv("SENTRY_ENABLED", raising=False)
    monkeypatch.setenv("SENTRY_DSN", "https://public@example.ingest.sentry.io/42")
    assert not sentry_monitoring.init_sentry()


def test_http_dsn_rejected(monkeypatch):
    from app.core import sentry_monitoring
    monkeypatch.setattr(sentry_monitoring, "_INITIALIZED", False)
    monkeypatch.setenv("SENTRY_ENABLED", "true")
    monkeypatch.setenv("SENTRY_DSN", "http://public@example.ingest.sentry.io/42")
    assert not sentry_monitoring.init_sentry()
