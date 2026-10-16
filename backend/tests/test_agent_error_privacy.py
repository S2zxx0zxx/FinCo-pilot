from unittest.mock import AsyncMock
import uuid

import pytest

from app.agents.providers.base import (
    LLMAuthError, LLMRateLimitError, LLMUnavailableError, LLMNotSupportedError,
    LLMError, ToolCall,
)
from app.agents.runtime.executor import _classify_error, _safe_call_tool


@pytest.mark.parametrize('kind', [LLMAuthError, LLMRateLimitError, LLMUnavailableError, LLMNotSupportedError, LLMError, ValueError])
@pytest.mark.parametrize('expose_detail', [True, False])
def test_executor_never_relays_raw_provider_exception(kind, expose_detail):
    code, message = _classify_error(kind('synthetic-secret account=123'), expose_detail=expose_detail)
    assert code
    assert 'synthetic-secret' not in message
    assert 'account=123' not in message


@pytest.mark.asyncio
async def test_tool_failure_does_not_relay_financial_exception_to_model_or_logs(caplog):
    mcp = AsyncMock()
    mcp.call.side_effect = RuntimeError('synthetic-secret account=123')
    with caplog.at_level('WARNING', logger='app.agents.runtime.executor'):
        result = await _safe_call_tool(mcp, ToolCall(id='a', name='safe_tool', arguments={}),
                                      user_id=uuid.uuid4(), conversation_id=uuid.uuid4())
    assert result['ok'] is False
    assert 'synthetic-secret' not in str(result) + caplog.text
    assert 'account=123' not in str(result) + caplog.text
    assert 'RuntimeError' in result['text']
