import json
from pathlib import Path

import pytest

from app.application.services.agent_service import AgentService
from app.core.config import settings
from app.core.dependencies import resolve_llm_provider
from app.infrastructure.llm.provider_errors import RetryableError
from tests.evals.agent_evaluator import AgentEvaluator
from tests.fixtures.fakes import FakeSearchEngine, make_fake_chunk


def _is_rate_limit(exc: Exception) -> bool:
    message = str(exc).lower()
    return (
        "429" in message
        or "rate limit" in message
        or "quota" in message
        or "resource_exhausted" in message
    )


@pytest.mark.asyncio
async def test_agent_intent_evaluator_with_fake_provider():
    evaluator = AgentEvaluator(live=False)
    result = await evaluator.evaluate()

    assert result.total > 0
    assert result.correct == result.total
    assert result.accuracy == 1.0
    assert all(stats["correct"] == stats["total"] for stats in result.per_intent.values())


@pytest.mark.llm
@pytest.mark.asyncio
async def test_agent_intent_evaluator_with_live_provider():
    if not settings.is_llm_configured:
        pytest.skip("No live LLM API key configured")

    agent = AgentService(
        search_engine=FakeSearchEngine(chunks=[make_fake_chunk()]),
        llm_provider=resolve_llm_provider(),
    )
    evaluator = AgentEvaluator(agent=agent, live=True)

    try:
        result = await evaluator.evaluate()
    except RetryableError as exc:
        if _is_rate_limit(exc):
            pytest.skip(f"Live LLM rate-limited: {exc}")
        raise

    assert result.total > 0
    # We expect the live model to be reasonably accurate, but we don't enforce
    # 100% to avoid flaky failures due to model variation.
    assert result.accuracy >= 0.75


def test_agent_eval_dataset_is_valid_jsonl():
    dataset_path = Path(__file__).with_name("agent_eval_dataset.jsonl")
    examples = []
    with dataset_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            assert "question" in data
            assert "expected_intent" in data
            examples.append(data)

    assert len(examples) >= 4
    intents = {e["expected_intent"] for e in examples}
    assert intents >= {"search", "compare", "extract", "summarize"}
