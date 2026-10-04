"""Check operator publication declarations; not a legal or live-service certification."""

from app.core.config import get_settings
from app.core.privacy_policy import VERSION, publication_blockers


def main() -> int:
    settings = get_settings()
    blockers = publication_blockers(settings)
    if not settings.privacy_policy_published:
        blockers.append("publication_disabled")
    print(f"Privacy notice version: {VERSION}")
    if blockers:
        print("Publication blocked: " + ", ".join(blockers))
        return 1
    print(
        "Publication declarations complete; verify the live URL and operational facts separately."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
