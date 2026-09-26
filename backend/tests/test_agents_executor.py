"""End-to-end-style executor tests with a scripted LLM and a fake MCP.

These exercise the full agent runtime — turn loop, tool dispatch, message
persistence, usage logging, error classification — without ever hitting a
real LLM or MCP server.

Pattern:
  - `_ScriptedProvider` yields a predetermined sequence of ChatChunks.
  - `_FakeMCP` exposes one synthetic tool and records calls.
  - We patch `_provider_for` and pass our fake MCP into AgentExecutor.
"""
import uuid
from typing import AsyncIterator
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.agents.mcp.client import MCPRegistry, ToolHandle
from app.agents.models.agent import Agent
from app.agents.models.conversation import Conversation, Message
from app.agents.models.usage import LlmUsage
from app.agents.providers.base import (
    ChatChunk,
    LLMAuthError,
    LLMProvider,
    Usage,
)
from app.agents.runtime.executor import AgentExecutor, ExecutorEvent


pytestmark = pytest.mark.asyncio


# --- Fakes -----------------------------------------------------------------


class _ScriptedProvider(LLMProvider):
    """Yields chunks from a list of "turns". Each turn is a list of chunks
    that simulate one model round. The provider iterates turns across
    successive chat_stream() calls."""

    name = "openai"  # match cost-table key for usage tests

    def __init__(self, turns: list[list[ChatChunk]]):
        super().__init__(api_key="x")
        self._turns = list(turns)

    async def chat_stream(  # type: ignore[override]
        self, messages, *, model, tools=None, temperature=0.4, max_tokens=None
    ) -> AsyncIterator[ChatChunk]:
        if not self._turns:
            # No more scripted turns — emit a generic finish.
            yield ChatChunk(type="finish", finish_reason="stop")
            return
        turn = self._turns.pop(0)
        for c in turn:
            yield c

    async def embed(self, texts, *, model):
        return [[0.0] * 4 for _ in texts]


class _FakeMCP(MCPRegistry):
    """In-process MCPRegistry that doesn't open any sockets. Discovers a
    single tool and records every call() invocation."""

    def __init__(self, *, tools: list[ToolHandle], canned_result: dict | None = None):
        # Skip parent __init__ so we don't try to construct real clients.
        self._tools = tools
        self._canned = canned_result or {"ok": True, "data": {"items": [{"hello": "world"}]}, "text": "ok"}
        self.calls: list[tuple[str, dict]] = []

    def server_names(self):
        return ["fincopilot"]

    async def discover(self, *, workspace_id=None, user_id, conversation_id=None, agent_id=None):
        return list(self._tools)

    async def call(self, *, wire_name, arguments, workspace_id=None, user_id, conversation_id=None, agent_id=None):
        self.calls.append((wire_name, arguments))
        return self._canned


# --- Helpers --------------------------------------------------------------


def _patch_provider(p: LLMProvider):
    return patch("app.agents.runtime.executor._provider_for", return_value=p)


async def _drain(executor: AgentExecutor, **kwargs) -> list[ExecutorEvent]:
    return [ev async for ev in executor.run(**kwargs)]


# --- Tests ----------------------------------------------------------------


async def test_simple_text_response_no_tools(session, test_user, test_agent: Agent, test_conversation: Conversation):
    """LLM returns a plain answer; no tool calls."""
    provider = _ScriptedProvider([[
        ChatChunk(type="text_delta", text="Hello "),
        ChatChunk(type="text_delta", text="world!"),
        ChatChunk(type="usage", usage=Usage(input_tokens=10, output_tokens=4)),
        ChatChunk(type="finish", finish_reason="stop"),
    ]])

    executor = AgentExecutor(mcp=_FakeMCP(tools=[]))
    with _patch_provider(provider):
        events = await _drain(
            executor,
            session=session,
            agent=test_agent,
            user_id=test_user.id,
            conversation_id=test_conversation.id,
            user_message="hi",
        )

    text_events = [e for e in events if e.type == "text_delta"]
    assert "".join(e.text or "" for e in text_events) == "Hello world!"
    assert events[-1].type == "done"
    assert events[-1].finish_reason == "stop"

    # Persisted: user msg + assistant msg.
    msgs = (await session.execute(
        select(Message).where(Message.conversation_id == test_conversation.id).order_by(Message.ordinal)
    )).scalars().all()
    roles = [m.role for m in msgs]
    assert roles == ["user", "assistant"]
    assert msgs[1].content == "Hello world!"
    assert msgs[1].input_tokens == 10
    assert msgs[1].output_tokens == 4


async def test_usage_row_recorded(session, test_user, test_agent, test_conversation):
    provider = _ScriptedProvider([[
        ChatChunk(type="text_delta", text="ok"),
        ChatChunk(type="usage", usage=Usage(input_tokens=100, output_tokens=20)),
        ChatChunk(type="finish", finish_reason="stop"),
    ]])
    executor = AgentExecutor(mcp=_FakeMCP(tools=[]))
    with _patch_provider(provider):
        await _drain(
            executor,
            session=session,
            agent=test_agent,
            user_id=test_user.id,
            conversation_id=test_conversation.id,
            user_message="hi",
        )
    rows = (await session.execute(
        select(LlmUsage).where(LlmUsage.conversation_id == test_conversation.id)
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0].input_tokens == 100
    assert rows[0].output_tokens == 20
    assert rows[0].provider == "openai"
    # gpt-4o-mini rates: (0.15, 0.60) per 1M.
    assert rows[0].cost_usd is not None
    assert float(rows[0].cost_usd) > 0


async def test_tool_call_dispatch_and_result_persisted(session, test_user, test_agent, test_conversation):
    """LLM emits a tool call; executor runs it via fake MCP and feeds the
    result back; second turn returns a plain answer."""
    tools = [ToolHandle(server="fincopilot", name="list_accounts", description="d", parameters={"type": "object"})]
    fake_mcp = _FakeMCP(tools=tools, canned_result={
        "ok": True, "data": {"items": [{"id": "a1", "name": "Checking"}]}, "text": "1 account",
    })

    provider = _ScriptedProvider([
        # Turn 1: emit a tool call.
        [
            ChatChunk(type="tool_call_start", tool_call_id="t1", tool_name="fincopilot__list_accounts"),
            ChatChunk(type="tool_call_args_delta", tool_call_id="t1", args_delta="{}"),
            ChatChunk(type="tool_call_end", tool_call_id="t1"),
            ChatChunk(type="usage", usage=Usage(input_tokens=20, output_tokens=5)),
            ChatChunk(type="finish", finish_reason="tool_calls"),
        ],
        # Turn 2: respond with the result.
        [
            ChatChunk(type="text_delta", text="You have 1 account."),
            ChatChunk(type="usage", usage=Usage(input_tokens=30, output_tokens=8)),
            ChatChunk(type="finish", finish_reason="stop"),
        ],
    ])

    executor = AgentExecutor(mcp=fake_mcp)
    with _patch_provider(provider):
        events = await _drain(
            executor,
            session=session,
            agent=test_agent,
            user_id=test_user.id,
            conversation_id=test_conversation.id,
            user_message="how many accounts?",
        )

    # Event stream: tool_call → tool_result → text_delta → done.
    types = [e.type for e in events]
    assert "tool_call" in types
    assert "tool_result" in types
    assert types[-1] == "done"

    # MCP got called with the right wire name.
    assert fake_mcp.calls == [("fincopilot__list_accounts", {})]

    # DB state: user, assistant(turn1, with tool_calls), tool, assistant(turn2, with text).
    msgs = (await session.execute(
        select(Message).where(Message.conversation_id == test_conversation.id).order_by(Message.ordinal)
    )).scalars().all()
    roles = [m.role for m in msgs]
    assert roles == ["user", "assistant", "tool", "assistant"]
    assert msgs[1].tool_calls and msgs[1].tool_calls[0]["name"] == "fincopilot__list_accounts"
    assert msgs[3].content == "You have 1 account."

    # Two usage rows, one per provider call.
    usage_rows = (await session.execute(
        select(LlmUsage).where(LlmUsage.conversation_id == test_conversation.id)
    )).scalars().all()
    assert len(usage_rows) == 2


async def test_provider_auth_error_surfaced_as_friendly_message(
    session, test_user, test_agent, test_conversation
):
    """An LLMAuthError becomes an error event with code=auth, not a 500."""

    class _BoomProvider(LLMProvider):
        name = "openai"

        async def chat_stream(self, *args, **kwargs):  # type: ignore[override]
            raise LLMAuthError("missing key")
            yield  # unreachable, makes this a generator

        async def embed(self, texts, *, model):
            return []

    executor = AgentExecutor(mcp=_FakeMCP(tools=[]))
    with _patch_provider(_BoomProvider()):
        events = await _drain(
            executor,
            session=session,
            agent=test_agent,
            user_id=test_user.id,
            conversation_id=test_conversation.id,
            user_message="hi",
        )

    err = next((e for e in events if e.type == "error"), None)
    assert err is not None
    assert err.error_code == "auth"
    done = next((e for e in events if e.type == "done"), None)
    assert done is not None and done.finish_reason == "error"


async def test_core_copilot_redacts_operator_provider_error_detail(
    session, test_user, test_workspace, test_conversation
):
    from app.agents.services.agent_service import ensure_core_copilot

    core = await ensure_core_copilot(session, test_workspace.id, test_user.id)
    test_conversation.agent_id = core.id
    await session.commit()

    class _BoomProvider(LLMProvider):
        name = "openai_compatible"

        async def chat_stream(self, *args, **kwargs):  # type: ignore[override]
            raise LLMAuthError("secret-host.internal/v1 key=operator-secret")
            yield  # pragma: no cover

        async def embed(self, texts, *, model):
            return []

    executor = AgentExecutor(mcp=_FakeMCP(tools=[]))
    with _patch_provider(_BoomProvider()), patch.dict(
        "os.environ",
        {"AGENTS_DEFAULT_MODEL": "core-model"},
        clear=False,
    ):
        events = await _drain(
            executor,
            session=session,
            agent=core,
            user_id=test_user.id,
            workspace_id=test_workspace.id,
            conversation_id=test_conversation.id,
            user_message="hi",
        )

    err = next((e for e in events if e.type == "error"), None)
    assert err is not None
    assert err.error_code == "auth"
    assert "operator-secret" not in (err.error_message or "")
    assert "secret-host.internal" not in (err.error_message or "")
    assert "FinCo Copilot" in (err.error_message or "")


async def test_no_model_configured_yields_config_error(session, test_user, test_conversation):
    """An agent without model and without AGENTS_DEFAULT_MODEL should bail
    early with a config error rather than calling the provider."""
    bare_agent = Agent(
        id=uuid.uuid4(),
        user_id=test_user.id,
        name="Bare",
        provider="openai",
        model=None,  # the missing piece
    )
    session.add(bare_agent)
    await session.commit()

    # Reuse the existing conversation but switch its agent to the bare one.
    test_conversation.agent_id = bare_agent.id
    await session.commit()

    executor = AgentExecutor(mcp=_FakeMCP(tools=[]))
    # Provider doesn't matter here — should never be called.
    provider = _ScriptedProvider([])
    with _patch_provider(provider), patch.dict("os.environ", {"AGENTS_DEFAULT_MODEL": ""}, clear=False):
        events = await _drain(
            executor,
            session=session,
            agent=bare_agent,
            user_id=test_user.id,
            conversation_id=test_conversation.id,
            user_message="hi",
        )
    err = next((e for e in events if e.type == "error"), None)
    assert err is not None and err.error_code == "config"


async def test_per_agent_tool_whitelist_filters_discovery(
    session, test_user, test_agent, test_conversation
):
    """If the agent has explicit tool whitelist rows, the executor only
    sends the enabled ones to the LLM."""
    from app.agents.services import agent_service

    # Discover 2 tools, but only enable one.
    tools = [
        ToolHandle(server="fincopilot", name="list_accounts", description="", parameters={"type": "object"}),
        ToolHandle(server="fincopilot", name="list_categories", description="", parameters={"type": "object"}),
    ]
    fake_mcp = _FakeMCP(tools=tools)
    await agent_service.replace_tool_enablement(
        session, test_agent.id,
        [("fincopilot", "list_accounts", True), ("fincopilot", "list_categories", False)],
    )

    captured_tool_names: list[str] = []

    class _Capture(_ScriptedProvider):
        async def chat_stream(self, messages, *, model, tools=None, temperature=0.4, max_tokens=None):
            captured_tool_names.extend([t.name for t in (tools or [])])
            async for c in super().chat_stream(messages, model=model, tools=tools, temperature=temperature, max_tokens=max_tokens):
                yield c

    provider = _Capture([[
        ChatChunk(type="text_delta", text="ok"),
        ChatChunk(type="finish", finish_reason="stop"),
    ]])

    executor = AgentExecutor(mcp=fake_mcp)
    with _patch_provider(provider):
        await _drain(
            executor,
            session=session,
            agent=test_agent,
            user_id=test_user.id,
            conversation_id=test_conversation.id,
            user_message="hi",
        )

    assert captured_tool_names == ["fincopilot__list_accounts"]


async def test_tool_result_passed_to_llm_in_full(session, test_user, test_agent, test_conversation):
    """Regression: the executor used to truncate the tool result text to
    1500 chars before feeding it back to the model, causing the LLM to
    report "truncated" rows for any list response over a few items.
    The LLM must see the full structured payload."""
    big_items = [{"id": f"id-{i}", "description": f"Transaction number {i}", "amount": i * 10} for i in range(20)]
    fake_mcp = _FakeMCP(
        tools=[ToolHandle(server="fincopilot", name="list_transactions", description="d", parameters={"type": "object"})],
        canned_result={
            "ok": True,
            "data": {"items": big_items, "total": 20},
            "text": "long unused text",
        },
    )

    captured_tool_messages: list[str] = []

    class _Capture(_ScriptedProvider):
        async def chat_stream(self, messages, *, model, tools=None, temperature=0.4, max_tokens=None):
            captured_tool_messages.extend([m.content for m in messages if m.role == "tool"])
            async for c in super().chat_stream(messages, model=model, tools=tools, temperature=temperature, max_tokens=max_tokens):
                yield c

    provider = _Capture([
        # Turn 1: emit a tool call.
        [
            ChatChunk(type="tool_call_start", tool_call_id="t1", tool_name="fincopilot__list_transactions"),
            ChatChunk(type="tool_call_args_delta", tool_call_id="t1", args_delta="{}"),
            ChatChunk(type="tool_call_end", tool_call_id="t1"),
            ChatChunk(type="finish", finish_reason="tool_calls"),
        ],
        # Turn 2: text reply.
        [
            ChatChunk(type="text_delta", text="ok"),
            ChatChunk(type="finish", finish_reason="stop"),
        ],
    ])

    executor = AgentExecutor(mcp=fake_mcp)
    with _patch_provider(provider):
        await _drain(
            executor,
            session=session,
            agent=test_agent,
            user_id=test_user.id,
            conversation_id=test_conversation.id,
            user_message="list me everything",
        )

    assert captured_tool_messages, "executor should have fed a tool message into turn 2"
    last = captured_tool_messages[-1]
    # Every item must appear in the LLM-facing content — no silent truncation.
    for i in range(20):
        assert f"Transaction number {i}" in last, (
            f"item {i} missing from tool message of length {len(last)} — likely truncation regression"
        )


async def test_auto_context_primer_prepended_when_enabled(session, test_user, test_agent, test_conversation, test_account):
    """Captures the system messages the provider sees and verifies the
    primer is the first one when auto_context=True (default), with the
    agent's own system_prompt right after."""
    captured: dict[str, list] = {"system": []}

    class _Capture(_ScriptedProvider):
        async def chat_stream(self, messages, *, model, tools=None, temperature=0.4, max_tokens=None):
            captured["system"] = [m.content for m in messages if m.role == "system"]
            async for c in super().chat_stream(messages, model=model, tools=tools, temperature=temperature, max_tokens=max_tokens):
                yield c

    provider = _Capture([[
        ChatChunk(type="text_delta", text="ok"),
        ChatChunk(type="finish", finish_reason="stop"),
    ]])
    executor = AgentExecutor(mcp=_FakeMCP(tools=[]))
    test_agent.auto_context = True
    test_agent.system_prompt = "You are helpful."
    await session.commit()

    with _patch_provider(provider):
        await _drain(
            executor,
            session=session,
            agent=test_agent,
            user_id=test_user.id,
            conversation_id=test_conversation.id,
            user_message="hi",
        )
    sys_msgs = captured["system"]
    # Stack: guardrail [0] + identity primer [1] + agent system_prompt [2] + auto-context [3].
    assert len(sys_msgs) == 4, f"expected guardrail + identity + agent prompt + auto-context, got {len(sys_msgs)}"
    assert "Runtime rules" in sys_msgs[0]
    assert "propose_" in sys_msgs[0]
    assert "obligations_reviewed=true" in sys_msgs[0]
    assert "explicitly confirms" in sys_msgs[0]
    assert "FinCo-Pilot" in sys_msgs[1]            # identity primer mentions the product
    assert sys_msgs[2] == "You are helpful."
    assert "Context for this conversation" in sys_msgs[3]
    assert "test@example.com" in sys_msgs[3]  # uses test_user fixture's email
    assert "Conta Corrente" in sys_msgs[3]    # account name from fixture


async def test_auto_context_primer_skipped_when_disabled(session, test_user, test_agent, test_conversation):
    captured: dict[str, list] = {"system": []}

    class _Capture(_ScriptedProvider):
        async def chat_stream(self, messages, *, model, tools=None, temperature=0.4, max_tokens=None):
            captured["system"] = [m.content for m in messages if m.role == "system"]
            async for c in super().chat_stream(messages, model=model, tools=tools, temperature=temperature, max_tokens=max_tokens):
                yield c

    provider = _Capture([[
        ChatChunk(type="text_delta", text="ok"),
        ChatChunk(type="finish", finish_reason="stop"),
    ]])
    executor = AgentExecutor(mcp=_FakeMCP(tools=[]))
    test_agent.auto_context = False
    test_agent.system_prompt = "Just the agent prompt."
    await session.commit()

    with _patch_provider(provider):
        await _drain(
            executor,
            session=session,
            agent=test_agent,
            user_id=test_user.id,
            conversation_id=test_conversation.id,
            user_message="hi",
        )
    sys_msgs = captured["system"]
    # Guardrail [0] + identity [1] + agent prompt [2]; no auto-context primer.
    assert len(sys_msgs) == 3
    assert "Runtime rules" in sys_msgs[0]
    assert "FinCo-Pilot" in sys_msgs[1]
    assert sys_msgs[2] == "Just the agent prompt."


async def test_runtime_guardrail_always_present_even_with_no_agent_prompt(session, test_user, test_agent, test_conversation):
    """Even when the user gave their agent no system_prompt and disabled
    auto_context, the runtime guardrail must still be there."""
    captured: dict[str, list] = {"system": []}

    class _Capture(_ScriptedProvider):
        async def chat_stream(self, messages, *, model, tools=None, temperature=0.4, max_tokens=None):
            captured["system"] = [m.content for m in messages if m.role == "system"]
            async for c in super().chat_stream(messages, model=model, tools=tools, temperature=temperature, max_tokens=max_tokens):
                yield c

    provider = _Capture([[ChatChunk(type="text_delta", text="ok"), ChatChunk(type="finish", finish_reason="stop")]])
    executor = AgentExecutor(mcp=_FakeMCP(tools=[]))
    test_agent.auto_context = False
    test_agent.system_prompt = ""
    await session.commit()

    with _patch_provider(provider):
        await _drain(
            executor, session=session, agent=test_agent,
            user_id=test_user.id, conversation_id=test_conversation.id,
            user_message="hi",
        )
    sys_msgs = captured["system"]
    # Guardrail [0] + identity primer [1] are the irreducible minimum —
    # both are always present even when the user gave no system_prompt
    # and turned auto-context off.
    assert len(sys_msgs) == 2
    assert "Runtime rules" in sys_msgs[0]
    assert "propose_" in sys_msgs[0]
    assert "FinCo-Pilot" in sys_msgs[1]


async def test_max_iterations_terminates_runaway_agent(session, test_user, test_agent, test_conversation):
    """If the LLM keeps emitting tool calls forever, executor stops at
    MAX_ITERS and emits a max_iterations error."""
    tools = [ToolHandle(server="fincopilot", name="loop_tool", description="", parameters={"type": "object"})]
    fake_mcp = _FakeMCP(tools=tools)

    # Same tool-call turn repeated indefinitely.
    def _looping_turn():
        return [
            ChatChunk(type="tool_call_start", tool_call_id=f"t{uuid.uuid4().hex[:6]}", tool_name="fincopilot__loop_tool"),
            ChatChunk(type="tool_call_args_delta", tool_call_id="t1", args_delta="{}"),
            ChatChunk(type="tool_call_end", tool_call_id="t1"),
            ChatChunk(type="finish", finish_reason="tool_calls"),
        ]

    provider = _ScriptedProvider([_looping_turn() for _ in range(20)])
    executor = AgentExecutor(mcp=fake_mcp)
    with _patch_provider(provider):
        events = await _drain(
            executor,
            session=session,
            agent=test_agent,
            user_id=test_user.id,
            conversation_id=test_conversation.id,
            user_message="loop forever",
        )

    err = next((e for e in events if e.type == "error"), None)
    done = next((e for e in events if e.type == "done"), None)
    assert err is not None and err.error_code == "max_iterations"
    assert done is not None and done.finish_reason == "max_iterations"


async def test_core_copilot_exposes_only_explicit_reads_and_proposals(
    session, test_user, test_workspace, test_conversation
):
    from app.agents.services.agent_service import ensure_core_copilot

    core = await ensure_core_copilot(session, test_workspace.id, test_user.id)
    test_conversation.agent_id = core.id
    await session.commit()

    tools = [
        ToolHandle(
            server="fincopilot",
            name="list_accounts",
            description="read",
            parameters={"type": "object", "properties": {}},
            tags=("read", "accounts"),
        ),
        ToolHandle(
            server="fincopilot",
            name="propose_create_budget",
            description="proposal",
            parameters={"type": "object", "properties": {}},
            is_proposal=True,
            tags=("propose", "budgets"),
        ),
        ToolHandle(
            server="fincopilot",
            name="dangerous_admin_action",
            description="future unclassified action",
            parameters={"type": "object", "properties": {}},
            tags=(),
        ),
        ToolHandle(
            server="untrusted-extra",
            name="read_everything",
            description="operator-added MCP tool claiming to be read-only",
            parameters={"type": "object", "properties": {}},
            tags=("read",),
        ),
    ]
    fake_mcp = _FakeMCP(tools=tools)
    captured_tool_names: list[str] = []
    captured_max_tokens: list[int | None] = []

    class _Capture(_ScriptedProvider):
        async def chat_stream(self, messages, *, model, tools=None, temperature=0.4, max_tokens=None):
            captured_tool_names.extend([t.name for t in (tools or [])])
            captured_max_tokens.append(max_tokens)
            async for chunk in super().chat_stream(
                messages,
                model=model,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens,
            ):
                yield chunk

    provider = _Capture([[
        ChatChunk(type="text_delta", text="ok"),
        ChatChunk(type="finish", finish_reason="stop"),
    ]])
    executor = AgentExecutor(mcp=fake_mcp)
    with _patch_provider(provider), patch.dict(
        "os.environ",
        {"AGENTS_DEFAULT_MODEL": "core-model"},
        clear=False,
    ):
        await _drain(
            executor,
            session=session,
            agent=core,
            user_id=test_user.id,
            workspace_id=test_workspace.id,
            conversation_id=test_conversation.id,
            user_message="help me",
            allow_proposals=True,
        )

    assert "fincopilot__list_accounts" in captured_tool_names
    assert "fincopilot__propose_create_budget" in captured_tool_names
    assert "fincopilot__dangerous_admin_action" not in captured_tool_names
    assert "untrusted-extra__read_everything" not in captured_tool_names
    assert captured_max_tokens == [executor.settings.core_copilot_max_output_tokens]


async def test_bare_tool_name_is_rejected_when_multiple_servers_define_it(
    session, test_user, test_agent, test_conversation
):
    tools = [
        ToolHandle(
            server="fincopilot",
            name="same_name",
            description="first",
            parameters={"type": "object", "properties": {}},
            tags=("read",),
        ),
        ToolHandle(
            server="extra",
            name="same_name",
            description="second",
            parameters={"type": "object", "properties": {}},
            tags=("read",),
        ),
    ]
    fake_mcp = _FakeMCP(tools=tools)
    provider = _ScriptedProvider([
        [
            ChatChunk(
                type="tool_call_start",
                tool_call_id="ambiguous-1",
                tool_name="same_name",
            ),
            ChatChunk(
                type="tool_call_args_delta",
                tool_call_id="ambiguous-1",
                args_delta="{}",
            ),
            ChatChunk(type="finish", finish_reason="tool_calls"),
        ],
        [
            ChatChunk(type="text_delta", text="Could not call it."),
            ChatChunk(type="finish", finish_reason="stop"),
        ],
    ])

    executor = AgentExecutor(mcp=fake_mcp)
    with _patch_provider(provider):
        events = await _drain(
            executor,
            session=session,
            agent=test_agent,
            user_id=test_user.id,
            conversation_id=test_conversation.id,
            user_message="use the tool",
        )

    assert fake_mcp.calls == []
    blocked = next(e for e in events if e.type == "tool_result")
    assert blocked.tool_result is not None
    assert blocked.tool_result["ok"] is False


async def test_viewer_cannot_dispatch_hidden_proposal_even_if_model_hallucinates_it(
    session, test_user, test_agent, test_conversation
):
    tools = [
        ToolHandle(
            server="fincopilot",
            name="list_accounts",
            description="read",
            parameters={"type": "object", "properties": {}},
            tags=("read", "accounts"),
        ),
        ToolHandle(
            server="fincopilot",
            name="propose_create_budget",
            description="proposal",
            parameters={"type": "object", "properties": {}},
            is_proposal=True,
            tags=("propose", "budgets"),
        ),
    ]
    fake_mcp = _FakeMCP(tools=tools)
    provider = _ScriptedProvider([
        [
            ChatChunk(
                type="tool_call_start",
                tool_call_id="forbidden-1",
                tool_name="fincopilot__propose_create_budget",
            ),
            ChatChunk(
                type="tool_call_args_delta",
                tool_call_id="forbidden-1",
                args_delta="{}",
            ),
            ChatChunk(type="finish", finish_reason="tool_calls"),
        ],
        [
            ChatChunk(type="text_delta", text="I cannot make that change here."),
            ChatChunk(type="finish", finish_reason="stop"),
        ],
    ])

    executor = AgentExecutor(mcp=fake_mcp)
    with _patch_provider(provider):
        events = await _drain(
            executor,
            session=session,
            agent=test_agent,
            user_id=test_user.id,
            conversation_id=test_conversation.id,
            user_message="change my budget",
            allow_proposals=False,
        )

    assert fake_mcp.calls == []
    blocked = next(e for e in events if e.type == "tool_result")
    assert blocked.tool_result is not None
    assert blocked.tool_result["ok"] is False
