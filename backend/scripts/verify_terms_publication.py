"""Check publication declarations without printing identities or secrets."""

from app.core.config import get_settings
from app.core.terms import VERSION, publication_blockers


def main() -> int:
    settings = get_settings()
    blockers = publication_blockers(settings)
    if not settings.terms_published:
        blockers.append("publication_disabled")
    print(f"Terms version: {VERSION}")
    if blockers:
        print("Publication blocked: " + ", ".join(blockers))
        return 1
    print("Declarations complete; verify actual operations, live URL and acceptance separately.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
