"""Operator-only first-admin bootstrap. No password/token command-line flags."""
import argparse
import asyncio
import getpass
import os
import stat
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.auth import UserManager
from app.core.config import get_settings
from app.core.database import async_session_maker, engine
from app.services.admin_bootstrap_service import CreateAdminRequest, log_bootstrap_success, provision_first_admin
from fastapi_users.db import SQLAlchemyUserDatabase
from app.models.user import User


def password_from_file(path: str) -> str:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
            raise ValueError("Password file must be private and regular")
        with os.fdopen(descriptor, closefd=False) as source:
            value = source.read(1024)
        return value.rstrip('\r\n')
    finally:
        os.close(descriptor)


async def run(body: CreateAdminRequest) -> None:
    settings = get_settings()
    if not settings.setup_enabled or not settings.local_auth_enabled:
        raise ValueError("Protected local bootstrap must be explicitly enabled")
    async with async_session_maker() as session:
        try:
            manager = UserManager(SQLAlchemyUserDatabase(session, User))
            user = await provision_first_admin(session, manager, body)
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        log_bootstrap_success(user)
        print(f"First admin bootstrap: PASS\nuser_id={user.id}\nbootstrap_closed=true\nnext=disable SETUP_ENABLED and remove SETUP_TOKEN; verify login/RBAC/MFA separately")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--email', required=True, help='Explicit operator-selected admin email')
    parser.add_argument('--currency', default='INR')
    parser.add_argument('--language', default='en')
    parser.add_argument('--name', default='')
    parser.add_argument('--password-file', help='Private regular file; otherwise secure interactive prompt')
    args = parser.parse_args(argv)
    try:
        if args.password_file:
            password = password_from_file(args.password_file)
        else:
            if not sys.stdin.isatty():
                raise ValueError('Interactive terminal or private password file required')
            password = getpass.getpass('Admin password: ')
            if password != getpass.getpass('Confirm password: '):
                raise ValueError('Passwords do not match')
        body = CreateAdminRequest(email=args.email, password=password, currency=args.currency,
                                  name=args.name, language=args.language)
        async def operation():
            try:
                await run(body)
            finally:
                await engine.dispose()
        asyncio.run(operation())
        return 0
    except Exception:
        # Validation and DB errors can include credentials/SQL values. Never echo.
        print('First admin bootstrap: FAIL (configuration/input/already provisioned); no secret printed', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
