from tests.evals.base_evaluator import EvaluationResult, LLMJudge

FAITHFULNESS_PROMPT = """Evaluate whether the ANSWER is faithful to the provided CONTEXT.
Faithful means the answer is fully supported by the context and does not introduce unsupported information.

CONTEXT:
{context}

QUESTION:
{question}

ANSWER:
{answer}

Return a JSON object with exactly these fields:
- "score": a float between 0.0 and 1.0, where 1.0 means fully faithful.
- "reasoning": a brief explanation of the score.
"""


class FaithfulnessEvaluator:
    def __init__(self, judge: LLMJudge | None = None):
        self.judge = judge or LLMJudge()

    async def evaluate(self, question: str, answer: str, context: str) -> EvaluationResult:
        prompt = FAITHFULNESS_PROMPT.format(context=context, question=question, answer=answer)
        result = await self.judge.judge(prompt)
        return EvaluationResult(
            score=float(result.get("score", 0.0)),
            reasoning=str(result.get("reasoning", "")),
        )
