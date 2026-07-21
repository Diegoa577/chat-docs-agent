"""Live end-to-end RAG quality eval (requires a configured LLM API key).

Unlike test_faithfulness.py / test_relevance.py — which test the evaluator
plumbing with a fake judge — this module runs the REAL answer-generation path
(real prompts, citation discipline, grounding instruction) with the real LLM
and judges the faithfulness/relevance of the actual answers.

Design: retrieval is faked with the real seeded-protocol excerpts so the test
needs no Postgres — only an API key. Run with: pytest -m llm tests/evals
"""

import pytest

from app.application.services.agent_service import AgentService
from app.core.config import settings
from app.core.dependencies import resolve_llm_provider
from app.infrastructure.llm.provider_errors import RetryableError
from tests.evals.base_evaluator import LLMJudge
from tests.evals.faithfulness import FaithfulnessEvaluator
from tests.evals.relevance import AnswerRelevanceEvaluator
from tests.fixtures.fakes import FakeSearchEngine, make_fake_chunk

MIN_SCORE = 0.7


def _is_rate_limit(exc: Exception) -> bool:
    message = str(exc).lower()
    return (
        "429" in message
        or "rate limit" in message
        or "quota" in message
        or "resource_exhausted" in message
    )

# Same excerpts as the seeded document in tests/conftest.py.
PROTOCOL_CHUNKS = [
    make_fake_chunk(
        content=(
            "Adult patients aged 18 to 65 years with rheumatoid arthritis may be "
            "included. Informed consent is required."
        ),
        document_name="test_protocol.txt",
    ),
    make_fake_chunk(
        content=(
            "Serious adverse events must be reported to the sponsor within 24 hours of awareness."
        ),
        document_name="test_protocol.txt",
    ),
    make_fake_chunk(
        content="The primary objective is to evaluate ACR20 response at Week 12.",
        document_name="test_protocol.txt",
    ),
]

QUESTIONS = [
    "What are the inclusion criteria for the study?",
    "How long do investigators have to report serious adverse events?",
    "What is the primary objective of the study?",
]


def _build_agent() -> AgentService:
    return AgentService(
        search_engine=FakeSearchEngine(chunks=PROTOCOL_CHUNKS),
        llm_provider=resolve_llm_provider(),
    )


@pytest.mark.llm
class TestLiveRAGQuality:
    @pytest.fixture(autouse=True)
    def _require_llm(self):
        if not settings.is_llm_configured:
            pytest.skip("No live LLM API key configured")

    async def test_real_answers_are_faithful_and_relevant(self):
        llm = resolve_llm_provider()
        agent = _build_agent()
        faithfulness = FaithfulnessEvaluator(judge=LLMJudge(llm_provider=llm))
        relevance = AnswerRelevanceEvaluator(judge=LLMJudge(llm_provider=llm))
        context = "\n\n".join(chunk.content for chunk in PROTOCOL_CHUNKS)

        for question in QUESTIONS:
            try:
                result = await agent.handle(question)
            except RetryableError as exc:
                if _is_rate_limit(exc):
                    pytest.skip(f"Live LLM rate-limited: {exc}")
                raise

            assert "[Source " in result.answer, (
                f"Answer for {question!r} has no [Source N] citation marker: {result.answer!r}"
            )

            faith = await faithfulness.evaluate(question, result.answer, context)
            assert faith.score >= MIN_SCORE, (
                f"Faithfulness {faith.score} for {question!r}: {faith.reasoning}"
            )

            rel = await relevance.evaluate(question, result.answer)
            assert rel.score >= MIN_SCORE, (
                f"Relevance {rel.score} for {question!r}: {rel.reasoning}"
            )

    async def test_out_of_context_question_is_refused(self):
        agent = _build_agent()

        try:
            result = await agent.handle("What is the recommended dosage of ibuprofen?")
        except RetryableError as exc:
            if _is_rate_limit(exc):
                pytest.skip(f"Live LLM rate-limited: {exc}")
            raise

        assert "don't have enough information" in result.answer.lower(), (
            f"Out-of-context question was not refused: {result.answer!r}"
        )
