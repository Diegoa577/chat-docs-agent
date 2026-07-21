from pathlib import Path

import pytest

from app.core.config import settings  # noqa: F401  # triggers catalog initialisation
from app.infrastructure.llm.model_catalog import (
    LLMProvider,
    get_default_model_config,
    get_model_config,
    get_models_for_provider,
    load_models_from_file,
    resolve_model_config,
)


class TestLoadModelsFromFile:
    def test_returns_empty_list_when_file_missing(self) -> None:
        models = load_models_from_file("/definitely/not/a/models.yaml")
        assert models == []

    def test_loads_valid_model_entries(self, tmp_path: Path) -> None:
        catalog = tmp_path / "models.yaml"
        catalog.write_text(
            """
models:
  - provider: openai
    model_id: gpt-5.4
    display_name: GPT-5.4
    default_temperature: 0.5
    supports_json_mode: true
    extra_params:
      max_tokens: 1024
""",
            encoding="utf-8",
        )

        models = load_models_from_file(catalog)
        assert len(models) == 1
        cfg = models[0]
        assert cfg.provider == LLMProvider.OPENAI
        assert cfg.model_id == "gpt-5.4"
        assert cfg.display_name == "GPT-5.4"
        assert cfg.default_temperature == 0.5
        assert cfg.supports_json_mode is True
        assert cfg.extra_params == {"max_tokens": 1024}

    def test_skips_invalid_entries_and_loads_valid_ones(self, tmp_path: Path) -> None:
        catalog = tmp_path / "models.yaml"
        catalog.write_text(
            """
models:
  - provider: gemini
    model_id: gemini-3.5-flash
  - provider: unknown
  - model_id: no-provider
""",
            encoding="utf-8",
        )

        models = load_models_from_file(catalog)
        assert len(models) == 1
        assert models[0].provider == LLMProvider.GEMINI
        assert models[0].model_id == "gemini-3.5-flash"

    def test_raises_when_models_is_not_a_list(self, tmp_path: Path) -> None:
        catalog = tmp_path / "models.yaml"
        catalog.write_text("models: not-a-list\n", encoding="utf-8")
        with pytest.raises(ValueError, match="'models' must be a list"):
            load_models_from_file(catalog)


class TestResolveModelConfig:
    def test_resolves_explicit_model(self) -> None:
        cfg = resolve_model_config("openai", "gpt-5.4")
        assert cfg.model_id == "gpt-5.4"
        assert cfg.provider == LLMProvider.OPENAI

    def test_resolves_default_when_model_id_omitted(self) -> None:
        cfg = resolve_model_config("openai")
        assert cfg.model_id == "gpt-5.4-mini"

    def test_resolves_unknown_model_id_to_default(self) -> None:
        cfg = resolve_model_config("openai", "unknown-model")
        assert cfg.model_id == "gpt-5.4-mini"

    def test_raises_for_unconfigured_provider(self) -> None:
        with pytest.raises(ValueError, match="No model configured for provider"):
            resolve_model_config("nonexistent")


class TestCatalogHelpers:
    def test_get_model_config_returns_none_for_unknown(self) -> None:
        assert get_model_config("openai", "not-real") is None

    def test_get_models_for_provider_returns_matching_configs(self) -> None:
        models = get_models_for_provider("gemini")
        assert all(cfg.provider == LLMProvider.GEMINI for cfg in models)

    def test_get_default_model_config_returns_first_model(self) -> None:
        cfg = get_default_model_config("gemini")
        assert cfg is not None
        assert cfg.model_id == "gemini-3.5-flash"

    def test_get_default_model_config_returns_first_openai_model(self) -> None:
        cfg = get_default_model_config("openai")
        assert cfg is not None
        assert cfg.model_id == "gpt-5.4-mini"


class TestLoadedCatalog:
    def test_catalog_contains_latest_provider_models(self) -> None:
        assert get_model_config("openai", "gpt-5.4") is not None
        assert get_model_config("openai", "gpt-5.4-mini") is not None
        assert get_model_config("gemini", "gemini-3-flash-preview") is not None
        assert get_model_config("gemini", "gemini-3.5-flash") is not None
        assert get_model_config("gemini", "gemini-2.5-flash") is not None
