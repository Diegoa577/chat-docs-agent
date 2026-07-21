import json
import re
from typing import Any

from app.domain.ports.llm_provider import LLMProvider
from app.infrastructure.llm.factory import get_llm_provider


class LLMJudge:
    def __init__(self, llm_provider: LLMProvider | None = None):
        self.llm_provider = llm_provider or get_llm_provider()

    async def judge(self, prompt: str, temperature: float = 0.0) -> dict[str, Any]:
        messages = [
            {
                "role": "system",
                "content": "You are an objective evaluator. Respond only with JSON.",
            },
            {"role": "user", "content": prompt},
        ]
        response = await self.llm_provider.complete(
            messages, temperature=temperature, max_tokens=512
        )
        return self._parse_json(response.content)

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        # Try to extract JSON from markdown code blocks if present.
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            text = match.group(1)
        return json.loads(text.strip())


class EvaluationResult:
    def __init__(self, score: float, reasoning: str):
        self.score = score
        self.reasoning = reasoning

    def __repr__(self) -> str:
        return f"EvaluationResult(score={self.score}, reasoning={self.reasoning})"
