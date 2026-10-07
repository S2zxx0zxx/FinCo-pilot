"""Disposable native PostgreSQL proof of incomplete provider inventory safety."""

import asyncio
import os
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import httpx
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.main import app  # noqa: F401  register all mapped models
from app.core.database import Base, engine
from app.models.account import Account
from app.models.bank_connection import BankConnection
from app.models.transaction import Transaction
from app.models.user import User
from app.models.workspace import Workspace
from app.providers.base import SessionExpiredError
from app.providers.enable_banking import EnableBankingProvider
from app.services.connection_service import sync_connection


async def main():
    if os.environ.get("FINCO_DISPOSABLE_DB_TEST") != "yes" or os.environ.get("CI") != "true":
        raise SystemExit("Refusing proof outside explicitly disposable CI")
    schema = "bank_proof_" + uuid.uuid4().hex
    isolated = create_async_engine(
        engine.url, connect_args={"server_settings": {"search_path": schema + ",public"}}
    )
    sessions = async_sessionmaker(isolated, expire_on_commit=False)
    try:
        async with engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        async with isolated.begin() as connection:
            await connection.run_sync(lambda sync: Base.metadata.create_all(sync, checkfirst=False))
            assert await connection.scalar(text("SELECT current_schema()")) == schema

        for response_status, expected in [(401, "expired"), (500, "error")]:
            user_id, workspace_id, connection_id, account_id = [uuid.uuid4() for _ in range(4)]
            previous_sync = datetime(2026, 1, 1, tzinfo=timezone.utc)
            async with sessions() as session:
                session.add(
                    User(
                        id=user_id,
                        email=f"{user_id}@example.invalid",
                        hashed_password="synthetic-unused",
                        is_active=True,
                        preferences={"currency_display": "EUR"},
                    )
                )
                await session.flush()
                session.add(
                    Workspace(
                        id=workspace_id, name="Synthetic bank proof", created_by_user_id=user_id
                    )
                )
                await session.flush()
                session.add(
                    BankConnection(
                        id=connection_id,
                        user_id=user_id,
                        workspace_id=workspace_id,
                        provider="enable_banking",
                        external_id="session-test",
                        institution_name="Synthetic bank",
                        credentials={"session_id": "session-test"},
                        logo_url="https://example.invalid/logo",
                        last_sync_at=previous_sync,
                    )
                )
                await session.flush()
                session.add(
                    Account(
                        id=account_id,
                        user_id=user_id,
                        workspace_id=workspace_id,
                        connection_id=connection_id,
                        external_id="account-1",
                        name="Retained account",
                        type="checking",
                        balance=Decimal("777.25"),
                        currency="EUR",
                    )
                )
                await session.flush()
                session.add(
                    Transaction(
                        user_id=user_id,
                        workspace_id=workspace_id,
                        account_id=account_id,
                        external_id="retained-transaction",
                        description="Retained history",
                        amount=Decimal("12.50"),
                        date=date(2026, 1, 1),
                        type="debit",
                        source="sync",
                    )
                )
                await session.commit()

            paths = []

            def handler(request):
                assert request.method == "GET", (
                    "No financial or authentication dispatch in synthetic read proof"
                )
                paths.append(request.url.path)
                if request.url.path.startswith("/sessions/"):
                    return httpx.Response(200, json={"accounts": ["account-1", "account-2"]})
                uid = request.url.path.split("/")[2]
                if uid == "account-2" and request.url.path.endswith("balances"):
                    return httpx.Response(response_status, json={"private": "financial-canary"})
                payload = {
                    "uid": uid,
                    "currency": "EUR",
                    "display_name": "Changed name",
                    "cash_account_type": "CACC",
                }
                if request.url.path.endswith("balances"):
                    payload = {"balances": [{"balance_amount": {"amount": "0", "currency": "EUR"}}]}
                return httpx.Response(200, json=payload)

            provider = EnableBankingProvider()
            transport = httpx.MockTransport(handler)

            def client():
                return httpx.AsyncClient(
                    base_url="https://api.enablebanking.com", transport=transport
                )

            async with sessions() as session:
                with (
                    patch("app.services.connection_service.get_provider", return_value=provider),
                    patch.object(provider, "_client", side_effect=client),
                ):
                    try:
                        await sync_connection(session, connection_id, workspace_id, user_id)
                    except (SessionExpiredError, httpx.HTTPStatusError) as exc:
                        assert "financial-canary" not in str(exc)
                    else:
                        raise AssertionError("Incomplete account inventory must fail")
            assert "/accounts/account-2/balances" in paths
            async with sessions() as session:
                account = await session.get(Account, account_id)
                connection = await session.get(BankConnection, connection_id)
                assert account is not None and connection is not None
                assert account.balance == Decimal("777.25") and account.name == "Retained account"
                assert connection.status == expected and connection.last_sync_at == previous_sync
                history = (
                    (
                        await session.execute(
                            select(Transaction).where(Transaction.account_id == account_id)
                        )
                    )
                    .scalars()
                    .all()
                )
                assert len(history) == 1 and history[0].description == "Retained history"

        def loan_handler(request):
            assert request.method == "GET"
            path = request.url.path
            if path.startswith("/sessions/"):
                body = {"accounts": ["account-1"]}
            elif path.endswith("/details"):
                body = {
                    "uid": "account-1",
                    "currency": "EUR",
                    "display_name": "Observed loan",
                    "cash_account_type": "LOAN",
                }
            elif path.endswith("/balances"):
                body = {
                    "balances": [
                        {
                            "balance_type": "ITAV",
                            "balance_amount": {"amount": "9999", "currency": "EUR"},
                        },
                        {
                            "balance_type": "CLBD",
                            "balance_amount": {"amount": "125.50", "currency": "EUR"},
                        },
                    ]
                }
            else:
                body = {"transactions": []}
            return httpx.Response(200, json=body)

        def loan_client():
            return httpx.AsyncClient(
                base_url="https://api.enablebanking.com",
                transport=httpx.MockTransport(loan_handler),
            )

        from app.schemas.account import AccountUpdate
        from app.services.account_service import update_account
        from app.services.dashboard_service import _account_balance_at

        async with sessions() as session:
            with (
                patch("app.services.connection_service.get_provider", return_value=provider),
                patch.object(provider, "_client", side_effect=loan_client),
            ):
                await sync_connection(session, connection_id, workspace_id, user_id)
                first_history = (
                    await session.scalars(
                        select(Transaction).where(Transaction.account_id == account_id)
                    )
                ).all()
                await sync_connection(session, connection_id, workspace_id, user_id)
            account = await session.get(Account, account_id)
            assert (
                account is not None
                and account.type == "loan"
                and account.balance == Decimal("-125.50")
            )
            assert await _account_balance_at(session, account, date.today()) == -125.50
            accounts = (
                await session.scalars(select(Account).where(Account.connection_id == connection_id))
            ).all()
            history = (
                await session.scalars(
                    select(Transaction).where(Transaction.account_id == account_id)
                )
            ).all()
            assert len(accounts) == 1 and len(history) == len(first_history)
            try:
                await update_account(
                    session, account_id, workspace_id, AccountUpdate(type="checking")
                )
            except ValueError:
                pass
            else:
                raise AssertionError("Provider liability cannot be edited into cash")
        print(
            "PASS: native Enable Banking liability mapping; booked loan repairs legacy checking in place; repeated sync preserves identity/history; aggregate subtracts debt; cash override blocked; synthetic HTTP"
        )
        print(
            "PASS: native bank inventory failure; synthetic HTTP second-account expiry/outage never replaces retained balance/history or stamps fresh sync; typed reconnect; safe diagnostics"
        )
    finally:
        await isolated.dispose()
        async with engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
