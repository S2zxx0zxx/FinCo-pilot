from types import SimpleNamespace
from typing import cast
import pytest

from app.agents.models.agent import Agent

from app.agents.providers.openai_compatible import OpenAICompatibleProvider
from app.agents.runtime.executor import _model_for, _provider_and_model_for, _provider_for


def test_omniroute_gateway_env_uses_openai_compatible_transport(monkeypatch):
    """FinCo's OmniRoute integration is protocol compatibility, not GPT usage.

    The production gateway is intentionally wired through the existing
    OpenAI-compatible transport while the requested model is the explicit
    free-only OmniRoute combo.
    """
    monkeypatch.setenv("AGENTS_DEFAULT_PROVIDER", "openai_compatible")
    monkeypatch.setenv("AGENTS_OPENAI_COMPAT_BASE_URL", "https://ai.example.test/v1")
    monkeypatch.setenv("AGENTS_OPENAI_COMPAT_API_KEY", "omniroute-test-key")
    monkeypatch.setenv("AGENTS_DEFAULT_MODEL", "fincopilot-free-smart")

    agent = cast(Agent, SimpleNamespace(provider=None, model=None))
    provider = _provider_for(agent)

    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.base_url == "https://ai.example.test/v1"
    assert provider.api_key == "omniroute-test-key"
    assert _model_for(agent) == "fincopilot-free-smart"


def test_agent_model_cannot_be_replaced_by_gateway_default(monkeypatch):
    """An explicit per-agent model stays authoritative over the env default."""
    monkeypatch.setenv("AGENTS_DEFAULT_MODEL", "fincopilot-free-smart")
    agent = cast(Agent, SimpleNamespace(provider="openai_compatible", model="fincopilot-free-smart"))

    assert _model_for(agent) == "fincopilot-free-smart"


@pytest.mark.asyncio
async def test_core_copilot_uses_operator_route_not_user_default_connection(
    monkeypatch, session, test_user, test_workspace
):
    """A custom Advanced-Agent connection must not silently reroute core Copilot.

    The core marker is server-signed, so this test must exercise a real
    system-created Copilot rather than constructing an unsigned lookalike.
    """
    from app.agents.services import agent_service, connection_service

    monkeypatch.setenv("AGENTS_DEFAULT_PROVIDER", "openai_compatible")
    monkeypatch.setenv("AGENTS_OPENAI_COMPAT_BASE_URL", "https://ai.example.test/v1")
    monkeypatch.setenv("AGENTS_OPENAI_COMPAT_API_KEY", "omniroute-test-key")
    monkeypatch.setenv("AGENTS_DEFAULT_MODEL", "fincopilot-free-smart")

    async def _must_not_read_user_default(*args, **kwargs):
        raise AssertionError("core Copilot must not resolve a user default LLM connection")

    monkeypatch.setattr(
        connection_service,
        "get_default_connection",
        _must_not_read_user_default,
    )
    agent = await agent_service.ensure_core_copilot(
        session,
        test_workspace.id,
        test_user.id,
    )
    assert agent_service.is_core_copilot(agent)

    provider, model = await _provider_and_model_for(session, agent)
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.base_url == "https://ai.example.test/v1"
    assert model == "fincopilot-free-smart"
