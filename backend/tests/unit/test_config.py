from app.core.config import Settings


class TestEmbeddingFallbackConfiguration:
    def test_local_fallback_provider_requires_no_api_key(self):
        settings = Settings(embedding_fallback_provider="bge")
        assert settings.is_embedding_fallback_configured is True

    def test_openai_fallback_without_key_is_not_configured(self):
        settings = Settings(embedding_fallback_provider="openai", openai_api_key=None)
        assert settings.is_embedding_fallback_configured is False

    def test_openai_fallback_with_placeholder_key_is_not_configured(self):
        settings = Settings(
            embedding_fallback_provider="openai", openai_api_key="your-openai-api-key"
        )
        assert settings.is_embedding_fallback_configured is False

    def test_openai_fallback_with_key_is_configured(self):
        settings = Settings(embedding_fallback_provider="openai", openai_api_key="sk-real-key")
        assert settings.is_embedding_fallback_configured is True

    def test_no_fallback_is_not_configured(self):
        settings = Settings(embedding_fallback_provider=None)
        assert settings.is_embedding_fallback_configured is False
