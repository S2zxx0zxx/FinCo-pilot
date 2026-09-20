"""Exercise one-time approval under concurrent HTTP requests on disposable PG.

Run only in the migration smoke CI database, after `alembic upgrade head`.
No mocks or SQLite: both requests use separate real database transactions.
"""
import asyncio
from datetime import datetime, timedelta, timezone
import os
import uuid

import httpx
from sqlalchemy import func, select
from sqlalchemy.engine import make_url

from app.core.auth import get_jwt_strategy
from app.core.config import get_settings
from app.core.database import async_session_maker
from app.main import app
from app.models.category import Category
from app.models.mcp_approval import MCPApproval
from app.models.mcp_token import ExternalMCPToken
from app.models.subscription import Subscription
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from mcp_server import tools as _tools  # noqa: F401  register real handlers
from mcp_server.auth import CallContext
from mcp_server.registry import call_tool


async def main() -> None:
    settings = get_settings()
    if (os.environ.get('FINCO_DISPOSABLE_DB_TEST') != 'yes' or settings.is_production
            or make_url(settings.database_url).database != 'finco_ci'):
        raise RuntimeError('This test requires explicit opt-in and the disposable finco_ci database')
    now = datetime.now(timezone.utc)
    uid, wid, tid = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    name = f'Concurrent approval {uuid.uuid4()}'
    async with async_session_maker() as session:
        user = User(id=uid, email=f'{uid}@example.invalid', hashed_password='synthetic-ci-no-password-login',
                    is_active=True, is_superuser=False, is_verified=True)
        session.add(user)
        await session.flush()
        workspace = Workspace(id=wid, name='Disposable approval test', kind='personal',
                              created_by_user_id=uid, billing_owner_user_id=uid)
        session.add(workspace)
        await session.flush()
        session.add(WorkspaceMember(workspace_id=wid, user_id=uid, role='owner'))
        session.add(Subscription(user_id=uid, plan='max', status='active', billing_interval='monthly',
                                 current_period_start=now, current_period_end=now + timedelta(days=30)))
        credential = ExternalMCPToken(id=tid, user_id=uid, workspace_id=wid,
                                     credential_stamp=get_jwt_strategy().stamp(user), allow_writes=True,
                                     expires_at=now + timedelta(hours=1))
        session.add(credential)
        await session.commit()
        bearer = await get_jwt_strategy().write_token(user)
        proposal = await call_tool(session, CallContext(user_id=uid, workspace_id=wid, external=True, token_id=tid),
                                   'propose_create_category', {'name': name, 'apply': True})
        assert proposal['requires_approval'] is True
        assert await session.scalar(select(func.count()).select_from(Category).where(Category.name == name)) == 0
    headers = {'Authorization': f'Bearer {bearer}', 'X-Workspace-Id': str(wid)}
    path = f"/api/agents/mcp-tokens/approvals/{proposal['approval_id']}/approve"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://ci') as client:
        results = await asyncio.gather(client.post(path, headers=headers), client.post(path, headers=headers))
        assert sorted(r.status_code for r in results) == [200, 409], [(r.status_code, r.text) for r in results]
        assert (await client.post(path, headers=headers)).status_code == 409
    async with async_session_maker() as session:
        assert await session.scalar(select(func.count()).select_from(Category).where(Category.name == name)) == 1
        approval = await session.get(MCPApproval, uuid.UUID(proposal['approval_id']))
        assert approval and approval.status == 'executed'
    print('PASS: real PostgreSQL concurrent approval executed exactly once; replay denied')


if __name__ == '__main__':
    asyncio.run(main())
