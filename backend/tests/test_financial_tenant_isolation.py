"""Real HTTP/JWT A/B ownership checks using synthetic disposable records only.

Positive owner controls prevent a 404/empty route from masquerading as isolation.
No auth, workspace, service or permission dependency is replaced.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.core.auth import get_jwt_strategy
from app.core.database import Base
from app.models.subscription import Subscription
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember


@pytest_asyncio.fixture
async def tenants(client, session, test_user, test_workspace):
    other = User(
        id=uuid.uuid4(),
        email="isolation-b@example.invalid",
        hashed_password=test_user.hashed_password,
        is_active=True,
        is_verified=True,
        is_superuser=False,
        preferences={"currency_display": "BRL"},
    )
    session.add(other)
    await session.flush()
    workspace = Workspace(
        id=uuid.uuid4(),
        name="Isolation B",
        kind="business",
        default_currency="BRL",
        created_by_user_id=other.id,
        billing_owner_user_id=other.id,
    )
    session.add(workspace)
    test_workspace.kind = "business"
    await session.flush()
    session.add(WorkspaceMember(workspace_id=workspace.id, user_id=other.id, role="owner"))
    now = datetime.now(timezone.utc)
    session.add(
        Subscription(
            user_id=other.id,
            plan="max",
            status="active",
            billing_interval="monthly",
            current_period_start=now,
            current_period_end=now + timedelta(days=31),
        )
    )
    await session.commit()
    result = []
    for label, user, ws in (("A", test_user, test_workspace), ("B", other, workspace)):
        headers = {
            "Authorization": "Bearer " + await get_jwt_strategy().write_token(user),
            "X-Workspace-Id": str(ws.id),
        }
        rows = {}

        async def create(resource, payload):
            # Client-supplied tenancy/ownership fields must never relocate a row.
            payload = {
                **payload,
                "workspace_id": str(workspace.id if label == "A" else test_workspace.id),
                "user_id": str(other.id if label == "A" else test_user.id),
            }
            if resource == "loans":  # This schema rejects unknown fields explicitly.
                payload.pop("workspace_id")
                payload.pop("user_id")
            response = await client.post("/api/" + resource, headers=headers, json=payload)
            assert response.status_code == 201, (resource, response.text)
            rows[resource] = response.json()
            table = Base.metadata.tables[resource.replace("-", "_")]
            stored_scope = await session.scalar(
                select(table.c.workspace_id).where(table.c.id == uuid.UUID(rows[resource]["id"]))
            )
            assert stored_scope == ws.id, resource
            return rows[resource]["id"]

        account = await create(
            "accounts", {"name": f"Private-{label}-account", "type": "checking", "currency": "BRL"}
        )
        category = await create("categories", {"name": f"Private-{label}-category"})
        await create("category-groups", {"name": f"Private-{label}-category-group"})
        await create("payees", {"name": f"Private-{label}-payee"})
        wallet = await create("asset-groups", {"name": f"Private-{label}-wallet"})
        await create(
            "assets",
            {
                "name": f"Private-{label}-asset",
                "type": "other",
                "currency": "BRL",
                "group_id": wallet,
                "current_value": "987.65",
            },
        )
        await create(
            "budgets", {"category_id": category, "amount": "123.45", "month": "2026-10-01"}
        )
        await create(
            "goals", {"name": f"Private-{label}-goal", "currency": "BRL", "target_amount": "1000"}
        )
        await create(
            "collections",
            {
                "name": f"Private-{label}-collection",
                "account_ids": [account],
                "wallet_ids": [wallet],
            },
        )
        await create(
            "recurring-transactions",
            {
                "description": f"Private-{label}-recurring",
                "account_id": account,
                "category_id": category,
                "amount": "123.45",
                "currency": "BRL",
                "type": "debit",
                "frequency": "monthly",
                "start_date": "2026-10-01",
                "auto_generate": False,
            },
        )
        await create(
            "transactions",
            {
                "description": f"Private-{label}-transaction",
                "account_id": account,
                "category_id": category,
                "amount": "42.17",
                "currency": "BRL",
                "type": "debit",
                "date": "2026-10-01",
            },
        )
        await create(
            "rules",
            {
                "name": f"Private-{label}-rule",
                "conditions": [
                    {"field": "description", "op": "contains", "value": "never-match-synthetic"}
                ],
                "actions": [{"op": "set_category", "value": category}],
                "apply_to_existing": False,
            },
        )
        await create("groups", {"name": f"Private-{label}-group"})
        await create(
            "loans",
            {
                "name": f"Private-{label}-loan",
                "principal": "1000",
                "annual_rate": "5",
                "term_months": 12,
                "first_due_date": "2026-11-01",
                "currency": "BRL",
            },
        )
        await create(
            "invoices",
            {
                "total": "123.45",
                "currency": "BRL",
                "notes": f"Private-{label}-invoice",
                "as_draft": True,
            },
        )
        result.append(
            {
                "headers": headers,
                "rows": rows,
                "workspace": str(ws.id),
                "user": str(user.id),
                "label": label,
            }
        )
    return result


@pytest.mark.parametrize(
    "resource",
    [
        "accounts",
        "categories",
        "category-groups",
        "payees",
        "asset-groups",
        "assets",
        "budgets",
        "goals",
        "collections",
        "recurring-transactions",
        "transactions",
        "rules",
        "groups",
        "loans",
        "invoices",
    ],
)
async def test_lists_and_foreign_object_mutations(client, tenants, resource):
    for actor, victim in (tenants, tenants[::-1]):
        own, foreign = actor["rows"][resource], victim["rows"][resource]
        listed = await client.get("/api/" + resource, headers=actor["headers"])
        assert listed.status_code == 200, listed.text
        assert own["id"] in listed.text
        assert foreign["id"] not in listed.text, listed.text
        payload = {"name": "unauthorized-edit"}
        if resource in ("transactions", "recurring-transactions"):
            payload = {"description": "unauthorized-edit"}
        elif resource == "budgets":
            payload = {"amount": "999"}
        elif resource == "invoices":
            payload = {"notes": "unauthorized-edit"}
        elif resource == "loans":
            payload = {"version": 1, "paid_installments": 1}
        rejected = await client.patch(
            f"/api/{resource}/{foreign['id']}", headers=actor["headers"], json=payload
        )
        assert rejected.status_code == 404, (resource, rejected.text)
        # Loans intentionally have archive/CAS update, no DELETE endpoint.
        if resource != "loans":
            rejected = await client.delete(
                f"/api/{resource}/{foreign['id']}", headers=actor["headers"]
            )
            assert rejected.status_code == (
                400 if resource in ("categories", "category-groups") else 404
            ), (resource, rejected.text)
        retained = await client.get("/api/" + resource, headers=victim["headers"])
        assert foreign["id"] in retained.text
        assert "unauthorized-edit" not in retained.text


@pytest.mark.parametrize(
    "kind",
    [
        "budget-category",
        "recurring-category-create",
        "recurring-category-update",
        "asset-wallet-create",
        "asset-wallet-update",
        "category-group-create",
        "category-group-update",
    ],
)
async def test_foreign_relationships_rejected_before_write(client, tenants, kind):
    actor, victim = tenants
    own, other = actor["rows"], victim["rows"]
    headers = actor["headers"]
    if kind == "budget-category":
        response = await client.post(
            "/api/budgets",
            headers=headers,
            json={"category_id": other["categories"]["id"], "amount": "99", "month": "2026-11-01"},
        )
    elif kind.startswith("recurring-category"):
        payload = {"category_id": other["categories"]["id"]}
        if kind.endswith("create"):
            payload.update(
                description="bad-link",
                account_id=own["accounts"]["id"],
                amount="99",
                currency="BRL",
                type="debit",
                frequency="monthly",
                start_date="2026-10-01",
            )
            response = await client.post(
                "/api/recurring-transactions", headers=headers, json=payload
            )
        else:
            response = await client.patch(
                "/api/recurring-transactions/" + own["recurring-transactions"]["id"],
                headers=headers,
                json=payload,
            )
    else:
        resource = "assets" if kind.startswith("asset") else "categories"
        target = "asset-groups" if resource == "assets" else "category-groups"
        payload = {"group_id": other[target]["id"]}
        if kind.endswith("create"):
            payload["name"] = "bad-link"
            if resource == "assets":
                payload.update(type="other", currency="BRL")
            response = await client.post("/api/" + resource, headers=headers, json=payload)
        else:
            response = await client.patch(
                f"/api/{resource}/{own[resource]['id']}", headers=headers, json=payload
            )
    assert response.status_code == 400, (kind, response.text)


READ_OBJECTS = [
    ("accounts", "/summary"),
    ("accounts", "/balance-history"),
    ("accounts", "/bills"),
    ("transactions", ""),
    ("transactions", "/transfer-pair"),
    ("transactions", "/transfer-candidates"),
    ("assets", ""),
    ("assets", "/values"),
    ("assets", "/value-trend"),
    ("assets", "/transactions"),
    ("goals", ""),
    ("payees", ""),
    ("loans", ""),
    ("invoices", ""),
    ("groups", ""),
    ("groups", "/members"),
    ("groups", "/transactions"),
    ("groups", "/balances"),
    ("groups", "/settlements"),
    ("transactions", "/attachments"),
    ("categories", "/rule-usage"),
]


@pytest.mark.parametrize("resource,suffix", READ_OBJECTS)
async def test_object_and_nested_reads_require_actual_ownership(client, tenants, resource, suffix):
    for actor, victim in (tenants, tenants[::-1]):
        own = await client.get(
            f"/api/{resource}/{actor['rows'][resource]['id']}{suffix}", headers=actor["headers"]
        )
        assert own.status_code == 200, (resource, suffix, own.text)
        foreign = await client.get(
            f"/api/{resource}/{victim['rows'][resource]['id']}{suffix}", headers=actor["headers"]
        )
        absent = await client.get(
            f"/api/{resource}/{uuid.uuid4()}{suffix}", headers=actor["headers"]
        )
        if resource == "categories":
            # This query intentionally returns an empty own-workspace rule set
            # for unknown IDs; it must never reveal the foreign rule.
            assert actor["rows"]["rules"]["id"] in own.text
            assert foreign.status_code == absent.status_code == 200
            assert foreign.json() == absent.json() == {"rules": []}
        else:
            assert foreign.status_code == absent.status_code == 404, (
                resource,
                suffix,
                foreign.text,
            )


async def test_workspace_header_search_and_exports_cannot_cross_tenants(client, tenants):
    import io
    import zipfile

    for actor, victim in (tenants, tenants[::-1]):
        spoofed = {**actor["headers"], "X-Workspace-Id": victim["workspace"]}
        for resource in actor["rows"]:
            denied = await client.get("/api/" + resource, headers=spoofed)
            assert denied.status_code == 404, (resource, denied.text)
        search = await client.get("/api/search", headers=actor["headers"], params={"q": "Private-"})
        assert search.status_code == 200
        assert f"Private-{actor['label']}" in search.text
        assert f"Private-{victim['label']}" not in search.text
        csv = await client.get("/api/transactions/export", headers=actor["headers"])
        assert csv.status_code == 200
        assert actor["rows"]["transactions"]["description"] in csv.text
        assert victim["rows"]["transactions"]["description"] not in csv.text
        archive = await client.get("/api/export/backup", headers=actor["headers"])
        assert archive.status_code == 200
        with zipfile.ZipFile(io.BytesIO(archive.content)) as backup:
            text = "\n".join(
                backup.read(name).decode() for name in backup.namelist() if name.endswith(".json")
            )
        assert actor["rows"]["transactions"]["id"] in text
        for row in victim["rows"].values():
            assert row["id"] not in text


async def test_bulk_mutations_do_not_touch_foreign_transactions(client, tenants):
    actor, victim = tenants
    foreign = victim["rows"]["transactions"]["id"]
    before = await client.get("/api/transactions/" + foreign, headers=victim["headers"])
    for route, payload in [
        ("bulk-categorize", {"category_id": actor["rows"]["categories"]["id"]}),
        ("bulk-add-tags", {"tags": ["unauthorized-tag"]}),
        ("bulk-remove-tags", {"tags": ["victim-tag"]}),
    ]:
        response = await client.patch(
            "/api/transactions/" + route,
            headers=actor["headers"],
            json={"transaction_ids": [foreign], **payload},
        )
        assert response.status_code == 200, response.text
        assert response.json()["updated"] == 0
    deleted = await client.post(
        "/api/transactions/bulk-delete",
        headers=actor["headers"],
        json={"transaction_ids": [foreign]},
    )
    assert deleted.status_code == 200 and deleted.json()["deleted"] == 0
    after = await client.get("/api/transactions/" + foreign, headers=victim["headers"])
    assert after.json() == before.json()


async def test_foreign_wallet_rejected_before_market_requests(client, tenants, monkeypatch):
    from app.services import asset_transaction_service

    async def forbidden(*args, **kwargs):
        pytest.fail("Foreign wallet must be rejected before provider I/O")

    from unittest.mock import AsyncMock

    provider = AsyncMock()
    provider.get_quote.side_effect = forbidden
    monkeypatch.setattr(asset_transaction_service, "get_market_price_provider", lambda: provider)
    actor, victim = tenants
    response = await client.post(
        "/api/assets/buy",
        headers=actor["headers"],
        json={
            "ticker": "SYNTHETIC",
            "quantity": "1",
            "price": "10",
            "date": "2026-10-01",
            "group_id": victim["rows"]["asset-groups"]["id"],
        },
    )
    assert response.status_code == 400


async def test_shared_workspace_read_and_editor_access_still_work(client, tenants, session):
    actor, owner = tenants
    membership = WorkspaceMember(
        workspace_id=uuid.UUID(owner["workspace"]), user_id=uuid.UUID(actor["user"]), role="viewer"
    )
    session.add(membership)
    await session.commit()
    shared = {**actor["headers"], "X-Workspace-Id": owner["workspace"]}
    for resource, row in owner["rows"].items():
        listing = await client.get("/api/" + resource, headers=shared)
        assert listing.status_code == 200, (resource, listing.text)
        assert row["id"] in listing.text, resource
    target = "/api/transactions/" + owner["rows"]["transactions"]["id"]
    response = await client.get(target, headers=shared)
    assert response.status_code == 200
    assert response.json()["description"] == owner["rows"]["transactions"]["description"]
    denied = await client.patch(target, headers=shared, json={"notes": "viewer-must-not-write"})
    assert denied.status_code == 403
    membership.role = "editor"
    await session.commit()
    allowed = await client.patch(target, headers=shared, json={"notes": "authorized-collaborator"})
    assert allowed.status_code == 200
    assert allowed.json()["notes"] == "authorized-collaborator"


async def test_malformed_legacy_group_links_do_not_expose_foreign_children(
    client, tenants, session
):
    from app.models.asset import Asset
    from app.models.category import Category

    actor, victim = tenants
    category = await session.get(Category, uuid.UUID(actor["rows"]["categories"]["id"]))
    asset = await session.get(Asset, uuid.UUID(actor["rows"]["assets"]["id"]))
    category.group_id = uuid.UUID(victim["rows"]["category-groups"]["id"])
    asset.group_id = uuid.UUID(victim["rows"]["asset-groups"]["id"])
    await session.commit()
    groups = await client.get("/api/category-groups", headers=victim["headers"])
    assert groups.status_code == 200
    assert category.name not in groups.text
    comparison = await client.get("/api/budgets/comparison", headers=actor["headers"])
    assert comparison.status_code == 200
    assert victim["rows"]["category-groups"]["name"] not in comparison.text
    wallets = await client.get("/api/asset-groups", headers=victim["headers"])
    assert wallets.status_code == 200
    group = next(row for row in wallets.json() if row["id"] == victim["rows"]["asset-groups"]["id"])
    assert group["asset_count"] == 1
    assert group["current_value"] == 987.65


async def test_generate_cannot_write_another_workspace_through_creator_identity(
    client, tenants, session
):
    from datetime import date
    from app.models.recurring_transaction import RecurringTransaction

    actor, victim = tenants
    row = await session.get(
        RecurringTransaction, uuid.UUID(actor["rows"]["recurring-transactions"]["id"])
    )
    # Legitimate collaborator-created row; creator remains unchanged after
    # that collaborator is downgraded to viewer in the foreign workspace.
    row.workspace_id = uuid.UUID(victim["workspace"])
    row.account_id = uuid.UUID(victim["rows"]["accounts"]["id"])
    row.category_id = uuid.UUID(victim["rows"]["categories"]["id"])
    row.auto_generate = True
    row.start_date = date.today()
    row.next_occurrence = date.today()
    session.add(
        WorkspaceMember(
            workspace_id=uuid.UUID(victim["workspace"]),
            user_id=uuid.UUID(actor["user"]),
            role="viewer",
        )
    )
    await session.commit()
    response = await client.post("/api/recurring-transactions/generate", headers=actor["headers"])
    assert response.status_code == 200
    assert response.json()["generated"] == 0
    await session.refresh(row)
    assert row.next_occurrence == date.today()


async def test_other_financial_relationships_are_not_authorized_by_the_outer_row(client, tenants):
    actor, victim = tenants
    own, foreign = actor["rows"], victim["rows"]
    cases = []
    for tracking, field, resource in [
        ("account", "account_id", "accounts"),
        ("asset", "asset_id", "assets"),
        ("asset_group", "asset_group_id", "asset-groups"),
    ]:
        link = {"tracking_type": tracking, field: foreign[resource]["id"]}
        cases.extend(
            [
                ("POST", "/api/goals", {"name": "bad-link", "target_amount": "100", **link}),
                ("PATCH", "/api/goals/" + own["goals"]["id"], link),
            ]
        )
    for field, resource in [
        ("account_id", "accounts"),
        ("category_id", "categories"),
        ("payee_id", "payees"),
    ]:
        base = {
            "description": "bad-link",
            "date": "2026-10-01",
            "amount": "1",
            "type": "debit",
            "currency": "BRL",
            "account_id": own["accounts"]["id"],
        }
        link = {field: foreign[resource]["id"]}
        cases.extend(
            [
                ("POST", "/api/transactions", {**base, **link}),
                ("PATCH", "/api/transactions/" + own["transactions"]["id"], link),
            ]
        )
    cases.extend(
        [
            (
                "PATCH",
                "/api/recurring-transactions/" + own["recurring-transactions"]["id"],
                {"account_id": foreign["accounts"]["id"]},
            ),
            (
                "POST",
                "/api/invoices",
                {"total": "1", "as_draft": True, "payee_id": foreign["payees"]["id"]},
            ),
            (
                "PATCH",
                "/api/invoices/" + own["invoices"]["id"],
                {"payee_id": foreign["payees"]["id"]},
            ),
        ]
    )
    for op, resource in [("set_category", "categories"), ("set_payee", "payees")]:
        cases.append(
            (
                "PATCH",
                "/api/rules/" + own["rules"]["id"],
                {"actions": [{"op": op, "value": foreign[resource]["id"]}]},
            )
        )
    for method, route, payload in cases:
        response = await client.request(method, route, headers=actor["headers"], json=payload)
        expected = 404 if route.startswith("/api/invoices") else 400
        assert response.status_code == expected, (method, route, response.text)
    for resource in ["assets", "categories", "recurring-transactions"]:
        field = "category_id" if resource == "recurring-transactions" else "group_id"
        # Existing valid links and intentional unlink/null behavior remain.
        route = f"/api/{resource}/{own[resource]['id']}"
        cleared = await client.patch(route, headers=actor["headers"], json={field: None})
        assert cleared.status_code == 200 and cleared.json()[field] is None


async def test_bank_import_attachment_and_investment_children_stay_scoped(
    client, tenants, session, monkeypatch
):
    from datetime import date
    from unittest.mock import AsyncMock
    from app.models.asset_transaction import AssetTransaction
    from app.models.bank_connection import BankConnection
    from app.models.import_log import ImportLog
    from app.models.transaction_attachment import TransactionAttachment
    from app.services import attachment_service, connection_service

    storage = AsyncMock()
    storage.download.return_value = b"synthetic attachment bytes"
    monkeypatch.setattr(attachment_service, "get_storage_provider", lambda: storage)
    provider = AsyncMock(side_effect=AssertionError("Foreign connection reached provider"))
    monkeypatch.setattr(connection_service, "create_connect_token", provider)
    for tenant in tenants:
        ws, user = uuid.UUID(tenant["workspace"]), uuid.UUID(tenant["user"])
        connection = BankConnection(
            id=uuid.uuid4(),
            user_id=user,
            workspace_id=ws,
            provider="pluggy",
            external_id=str(uuid.uuid4()),
            institution_name="Synthetic bank",
            credentials={"item_id": "synthetic-private-item"},
        )
        imported = ImportLog(
            id=uuid.uuid4(),
            user_id=user,
            workspace_id=ws,
            account_id=uuid.UUID(tenant["rows"]["accounts"]["id"]),
            filename="synthetic.csv",
            format="csv",
            transaction_count=0,
        )
        attachment = TransactionAttachment(
            id=uuid.uuid4(),
            user_id=user,
            workspace_id=ws,
            transaction_id=uuid.UUID(tenant["rows"]["transactions"]["id"]),
            filename="synthetic.pdf",
            storage_key=f"{ws}/synthetic.pdf",
            content_type="application/pdf",
            size=26,
        )
        trade = AssetTransaction(
            id=uuid.uuid4(),
            workspace_id=ws,
            asset_id=uuid.UUID(tenant["rows"]["assets"]["id"]),
            kind="buy",
            quantity=1,
            price=10,
            fee=0,
            date=date.today(),
        )
        session.add_all([connection, imported, attachment, trade])
        tenant["children"] = {
            "connection": str(connection.id),
            "import": str(imported.id),
            "attachment": str(attachment.id),
            "trade": str(trade.id),
        }
    await session.commit()
    for actor, victim in (tenants, tenants[::-1]):
        for endpoint, key in [
            ("/api/connections", "connection"),
            ("/api/import-logs", "import"),
            ("/api/assets/transactions", "trade"),
        ]:
            listing = await client.get(endpoint, headers=actor["headers"])
            assert listing.status_code == 200, listing.text
            assert actor["children"][key] in listing.text
            assert victim["children"][key] not in listing.text
            assert "synthetic-private-item" not in listing.text
        victim_tx = victim["rows"]["transactions"]["id"]
        own_tx = actor["rows"]["transactions"]["id"]
        own_attachment = f"/api/transactions/{own_tx}/attachments/{actor['children']['attachment']}"
        positive = await client.get(own_attachment, headers=actor["headers"])
        assert positive.status_code == 200 and positive.content == b"synthetic attachment bytes"
        storage.reset_mock()
        target = f"/api/transactions/{victim_tx}/attachments/{victim['children']['attachment']}"
        for method, payload in [
            ("GET", None),
            ("PATCH", {"filename": "forbidden.pdf"}),
            ("DELETE", None),
        ]:
            denied = await client.request(method, target, headers=actor["headers"], json=payload)
            assert denied.status_code == 404, denied.text
        storage.download.assert_not_awaited()
        storage.delete.assert_not_awaited()
        for method, endpoint, payload in [
            ("POST", f"/api/connections/{victim['children']['connection']}/reconnect-token", None),
            (
                "PATCH",
                f"/api/connections/{victim['children']['connection']}/settings",
                {"sync_enabled": False},
            ),
            ("DELETE", f"/api/connections/{victim['children']['connection']}", None),
            ("DELETE", f"/api/import-logs/{victim['children']['import']}", None),
            (
                "PATCH",
                f"/api/assets/transactions/{victim['children']['trade']}",
                {"notes": "forbidden"},
            ),
            ("DELETE", f"/api/assets/transactions/{victim['children']['trade']}", None),
        ]:
            denied = await client.request(method, endpoint, headers=actor["headers"], json=payload)
            assert denied.status_code == 404, (endpoint, denied.text)
    provider.assert_not_awaited()
