import json
from pathlib import Path
from unittest.mock import patch

from app.core.config import settings
from app.infrastructure.search.hybrid_search_engine import HybridSearchEngine


def eval_dataset():
    fixture_path = Path(__file__).parent / "fixtures" / "eval_dataset.json"
    with open(fixture_path) as f:
        return json.load(f)


async def test_retrieval_finds_relevant_chunks(db_session, seeded_document):
    """Test that retrieval returns chunks containing expected keywords."""
    search_engine = HybridSearchEngine(db_session)
    dataset = eval_dataset()

    # Mock query embedding to avoid API calls during tests
    with patch.object(
        HybridSearchEngine,
        "_get_query_embedding",
        return_value=[0.15] * settings.embedding_dimension,
    ):
        results = []
        for item in dataset[:3]:  # Test first 3 questions
            chunks = await search_engine.search(item["question"], top_k=5)
            contents = " ".join([chunk.content.lower() for chunk in chunks])

            matches = [keyword.lower() in contents for keyword in item["expected_answer_contains"]]
            recall = sum(matches) / len(matches) if matches else 0.0
            results.append(recall)

    avg_recall = sum(results) / len(results) if results else 0.0
    assert avg_recall >= 0.5, f"Average retrieval recall {avg_recall} is below threshold"
