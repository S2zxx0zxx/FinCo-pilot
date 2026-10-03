import uuid
import json

import pytest
from pydantic import SecretStr
from sqlalchemy import select

from app.agents.models.agent import Agent
from app.agents.models.connection import LlmConnection
from app.agents.services import agent_service, crypto
from app.core.config import get_settings
from app.models.bank_connection import BankConnection
from scripts.rotate_data_keys import rotate_data


def _install_keys(monkeypatch, *, encryption="", identity="", jwt="new-session-key", legacy=""):
    settings = get_settings().model_copy(update={
        "secret_key": SecretStr(jwt),
        "credential_encryption_key": SecretStr(encryption),
        "core_copilot_signing_key": SecretStr(identity),
        "legacy_data_keys": SecretStr(json.dumps({"credentials": [legacy], "copilot": [legacy]}) if legacy else ""),
    })
    monkeypatch.setattr(crypto, "get_settings", lambda: settings)
    monkeypatch.setattr(agent_service, "get_settings", lambda: settings)
    return settings


def test_session_rotation_does_not_invalidate_independent_data_keys(monkeypatch):
    _install_keys(monkeypatch, encryption="encryption-key", identity="identity-key", jwt="session-before")
    token = crypto.encrypt("synthetic-provider-credential")
    agent = Agent(id=uuid.uuid4(), workspace_id=uuid.uuid4(), user_id=uuid.uuid4())
    agent.extra = {"kind": "core_copilot", "system_managed": True, "version": 1,
                   "server_signature": agent_service._core_signature(
                       agent_id=agent.id, workspace_id=agent.workspace_id, user_id=agent.user_id, version=1)}
    _install_keys(monkeypatch, encryption="encryption-key", identity="identity-key", jwt="session-after")
    assert crypto.decrypt(token) == "synthetic-provider-credential"
    assert agent_service.is_core_copilot(agent)
    assert not agent_service.can_access_agent(agent, uuid.uuid4())


def test_explicit_legacy_ring_preserves_credentials_but_current_jwt_is_not_a_data_key(monkeypatch):
    _install_keys(monkeypatch, jwt="old-key")
    token = crypto.encrypt("synthetic-provider-credential")
    _install_keys(monkeypatch, encryption="new-data-key", identity="new-identity-key", jwt="old-key")
    assert crypto.decrypt(token) is None

    _install_keys(monkeypatch, encryption="new-data-key", identity="new-identity-key", legacy="old-key")
    assert crypto.decrypt(token) == "synthetic-provider-credential"
    new_token = crypto.encrypt("new-credential")
    _install_keys(monkeypatch, encryption="new-data-key", identity="new-identity-key")
    assert crypto.decrypt(new_token) == "new-credential"
    assert crypto.decrypt(token) is None


def test_legacy_encryption_key_cannot_authenticate_a_copilot_identity(monkeypatch):
    _install_keys(monkeypatch, jwt="legacy-credential-key")
    token = crypto.encrypt("credential")
    agent = Agent(id=uuid.uuid4(), workspace_id=uuid.uuid4(), user_id=uuid.uuid4())
    agent.extra = {"kind": "core_copilot", "system_managed": True, "version": 1,
                   "server_signature": agent_service._core_signature(
                       agent_id=agent.id, workspace_id=agent.workspace_id, user_id=agent.user_id, version=1)}
    settings = _install_keys(monkeypatch, encryption="new-credential-key", identity="new-identity-key")
    settings.legacy_data_keys = SecretStr(json.dumps({"credentials": ["legacy-credential-key"]}))
    assert crypto.decrypt(token) == "credential"
    assert not agent_service.is_core_copilot(agent)


@pytest.mark.asyncio
async def test_missing_identity_key_quarantines_existing_core_without_replacement(
    session, test_user, test_workspace, monkeypatch,
):
    _install_keys(monkeypatch, jwt="old-identity-key")
    core = await agent_service.ensure_core_copilot(session, test_workspace.id, test_user.id)
    core_id = core.id
    _install_keys(monkeypatch, identity="new-identity-key")
    assert not agent_service.is_core_copilot(core)
    assert not agent_service.can_access_agent(core, test_user.id)
    assert core not in await agent_service.list_agents(session, test_workspace.id)
    assert await agent_service.get_default_agent(session, test_workspace.id) is None
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await agent_service.ensure_core_copilot(session, test_workspace.id, test_user.id)
    assert exc.value.status_code == 503
    with pytest.raises(ValueError, match="cannot be deleted"):
        await agent_service.delete_agent(session, core_id, test_workspace.id)
    assert (await session.execute(select(Agent))).scalars().all() == [core]


@pytest.mark.asyncio
@pytest.mark.parametrize("old_key", ["old-data-key", " old-data-key "])
async def test_atomic_migration_preserves_ids_and_credentials_after_legacy_retirement(
    session, test_user, test_workspace, monkeypatch, old_key,
):
    _install_keys(monkeypatch, jwt=old_key)
    core = await agent_service.ensure_core_copilot(session, test_workspace.id, test_user.id)
    llm = LlmConnection(user_id=test_user.id, name="Original connection", kind="openai",
                        api_key_encrypted=crypto.encrypt("llm-credential"))
    bank = BankConnection(user_id=test_user.id, workspace_id=test_workspace.id,
                          provider="simplefin", external_id="synthetic", institution_name="Test bank",
                          credentials={"access_url_enc": crypto.encrypt("bank-credential"), "other": "preserved"})
    session.add_all([llm, bank])
    await session.commit()
    ids = (core.id, llm.id, bank.id)
    original = llm.api_key_encrypted
    _install_keys(monkeypatch, encryption="new-data-key", identity="new-identity-key", legacy=old_key)
    counts = await rotate_data(session)
    assert counts == {"llm_credentials": 1, "bank_credentials": 1, "copilot_identities": 1}
    assert llm.api_key_encrypted == original  # dry run never rewrites rows
    await rotate_data(session, apply=True)
    await session.commit()
    _install_keys(monkeypatch, encryption="new-data-key", identity="new-identity-key")
    assert crypto.decrypt(llm.api_key_encrypted) == "llm-credential"
    assert bank.credentials is not None
    assert crypto.decrypt(bank.credentials["access_url_enc"]) == "bank-credential"
    assert bank.credentials["other"] == "preserved"
    assert agent_service.is_core_copilot(core)
    assert (core.id, llm.id, bank.id) == ids


@pytest.mark.asyncio
async def test_migration_validates_every_row_before_any_mutation(session, test_user, monkeypatch):
    _install_keys(monkeypatch, jwt="old-key")
    first = LlmConnection(user_id=test_user.id, name="valid", kind="openai", api_key_encrypted=crypto.encrypt("valid"))
    broken = LlmConnection(user_id=test_user.id, name="broken", kind="openai", api_key_encrypted="corrupt-token")
    session.add_all([first, broken])
    await session.commit()
    original = first.api_key_encrypted
    _install_keys(monkeypatch, encryption="new-key", identity="identity-key", legacy="old-key")
    with pytest.raises(ValueError, match="Unreadable"):
        await rotate_data(session, apply=True)
    assert first.api_key_encrypted == original
