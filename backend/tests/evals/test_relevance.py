import pytest

from tests.evals.base_evaluator import LLMJudge
from tests.evals.relevance import AnswerRelevanceEvaluator
from tests.fixtures.fakes import FakeLLMProvider


@pytest.mark.asyncio
async def test_relevance_evaluator_returns_score():
    fake_provider = FakeLLMProvider(
        response='{"score": 0.9, "reasoning": "The answer directly addresses the question."}'
    )
    judge = LLMJudge(llm_provider=fake_provider)
    evaluator = AnswerRelevanceEvaluator(judge=judge)

    result = await evaluator.evaluate(
        question="What are the inclusion criteria?",
        answer="Patients must provide informed consent.",
    )

    assert result.score == 0.9
    assert "directly" in result.reasoning.lower()
