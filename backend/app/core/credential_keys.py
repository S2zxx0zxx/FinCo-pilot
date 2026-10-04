"""Independent credential key ring shared without importing application services."""
from app.core.config import get_settings


def data_keys() -> tuple[str, ...]:
    settings = get_settings()
    return tuple(dict.fromkeys(filter(None, (
        settings.credential_encryption_key.get_secret_value().strip()
        or settings.secret_key.get_secret_value(),
        *settings.legacy_keys_for("credentials"),
    ))))
