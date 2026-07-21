from tests.evals.base_evaluator import EvaluationResult, LLMJudge

RELEVANCE_PROMPT = """Evaluate whether the ANSWER is relevant to the QUESTION.
Relevant means the answer directly addresses the question and provides useful information.

QUESTION:
{question}

ANSWER:
{answer}

Return a JSON object with exactly these fields:
- "score": a float between 0.0 and 1.0, where 1.0 means highly relevant.
- "reasoning": a brief explanation of the score.
"""


class AnswerRelevanceEvaluator:
    def __init__(self, judge: LLMJudge | None = None):
        self.judge = judge or LLMJudge()

    async def evaluate(self, question: str, answer: str) -> EvaluationResult:
        prompt = RELEVANCE_PROMPT.format(question=question, answer=answer)
        result = await self.judge.judge(prompt)
        return EvaluationResult(
            score=float(result.get("score", 0.0)),
            reasoning=str(result.get("reasoning", "")),
        )
