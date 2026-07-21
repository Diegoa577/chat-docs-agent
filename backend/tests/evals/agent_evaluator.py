import json
from dataclasses import dataclass
from pathlib import Path

from app.application.services.agent_service import AgentService
from tests.fixtures.fakes import FakeLLMProvider, FakeSearchEngine, make_fake_chunk


@dataclass
class AgentEvalExample:
    question: str
    expected_intent: str


@dataclass
class AgentEvalResult:
    total: int
    correct: int
    accuracy: float
    per_intent: dict[str, dict[str, int]]

    def __repr__(self) -> str:
        return (
            f"AgentEvalResult(total={self.total}, correct={self.correct}, "
            f"accuracy={self.accuracy:.2%})"
        )


class AgentEvaluator:
    """Evaluate agent intent classification.

    In the default mode the evaluator injects a controlled FakeLLMProvider that
    returns the expected intent JSON, so the test is deterministic and free.
    When `live=True`, the evaluator uses the real LLM provider configured in
    the agent and asks the underlying model to classify the intent.
    """

    def __init__(
        self,
        agent: AgentService | None = None,
        dataset_path: Path | str | None = None,
        live: bool = False,
    ):
        self.dataset_path = Path(
            dataset_path or Path(__file__).with_name("agent_eval_dataset.jsonl")
        )
        self.live = live
        self.agent = agent

    def load_dataset(self) -> list[AgentEvalExample]:
        examples: list[AgentEvalExample] = []
        with self.dataset_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                examples.append(
                    AgentEvalExample(
                        question=data["question"],
                        expected_intent=data["expected_intent"],
                    )
                )
        return examples

    async def evaluate(self) -> AgentEvalResult:
        examples = self.load_dataset()
        correct = 0
        per_intent: dict[str, dict[str, int]] = {}

        for example in examples:
            agent = self.agent or self._build_fake_agent(example.expected_intent)
            result = await agent.handle(example.question)
            predicted = result.intent

            is_correct = predicted == example.expected_intent
            if is_correct:
                correct += 1

            intent_stats = per_intent.setdefault(
                example.expected_intent, {"total": 0, "correct": 0}
            )
            intent_stats["total"] += 1
            if is_correct:
                intent_stats["correct"] += 1

        total = len(examples)
        accuracy = correct / total if total else 0.0
        return AgentEvalResult(
            total=total,
            correct=correct,
            accuracy=accuracy,
            per_intent=per_intent,
        )

    def _build_fake_agent(self, expected_intent: str) -> AgentService:
        # The fake provider returns the expected intent JSON for routing, then a
        # generic answer for the tool execution.
        intent_response = json.dumps(
            {
                "intent": expected_intent,
                "params": {"document_names": ["protocol.pdf"]},
            }
        )
        return AgentService(
            search_engine=FakeSearchEngine(chunks=[make_fake_chunk()]),
            llm_provider=FakeLLMProvider(response=intent_response),
        )
