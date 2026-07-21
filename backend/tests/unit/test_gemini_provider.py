from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.infrastructure.llm.gemini_provider import GeminiProvider


def _make_provider() -> GeminiProvider:
    provider = GeminiProvider(api_key="fake-key", model="gemini-2.5-flash")
    provider.client.aio.models.generate_content = AsyncMock(
        return_value=SimpleNamespace(text="ok")
    )
    return provider


@pytest.mark.asyncio
async def test_complete_warns_when_tools_are_passed():
    provider = _make_provider()

    with patch("app.infrastructure.llm.gemini_provider.logger") as mock_logger:
        await provider.complete(
            messages=[{"role": "user", "content": "hi"}],
            tools=[{"name": "search"}],
        )

    mock_logger.warning.assert_called_once()
    assert mock_logger.warning.call_args.args[0] == "tools_not_supported_by_adapter"


@pytest.mark.asyncio
async def test_complete_without_tools_does_not_warn():
    provider = _make_provider()

    with patch("app.infrastructure.llm.gemini_provider.logger") as mock_logger:
        await provider.complete(messages=[{"role": "user", "content": "hi"}])

    mock_logger.warning.assert_not_called()
