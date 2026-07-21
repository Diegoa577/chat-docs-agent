import pytest

from tests.evals.base_evaluator import LLMJudge
from tests.evals.faithfulness import FaithfulnessEvaluator
from tests.fixtures.fakes import FakeLLMProvider


@pytest.mark.asyncio
async def test_faithfulness_evaluator_returns_score():
    fake_provider = FakeLLMProvider(
        response='{"score": 0.95, "reasoning": "The answer is fully supported by the context."}'
    )
    judge = LLMJudge(llm_provider=fake_provider)
    evaluator = FaithfulnessEvaluator(judge=judge)

    result = await evaluator.evaluate(
        question="What are the inclusion criteria?",
        answer="Informed consent is required.",
        context="Inclusion criteria: adult patients must provide informed consent.",
    )

    assert result.score == 0.95
    assert "supported" in result.reasoning.lower()
