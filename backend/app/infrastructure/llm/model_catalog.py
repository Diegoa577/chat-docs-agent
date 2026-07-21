from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, TypeAlias

import structlog
import yaml

logger = structlog.get_logger()


class LLMProvider(StrEnum):
    """Supported LLM providers."""

    OPENAI = "openai"
    GEMINI = "gemini"


class OpenAIModel(StrEnum):
    """OpenAI model identifiers."""

    GPT_5_4 = "gpt-5.4"
    GPT_5_4_MINI = "gpt-5.4-mini"


class GeminiModel(StrEnum):
    """Google Gemini model identifiers."""

    GEMINI_3_0_FLASH = "gemini-3-flash-preview"
    GEMINI_3_5_FLASH = "gemini-3.5-flash"
    GEMINI_2_5_FLASH = "gemini-2.5-flash"


SupportedModel: TypeAlias = OpenAIModel | GeminiModel


@dataclass(frozen=True)
class LLMModelConfig:
    """Immutable configuration for an LLM model.

    Captures provider-specific generation behavior so adapters can apply the
    right parameters without hard-coding assumptions in the service classes.

    ``model`` is optional and used for catalogued models that have a matching
    enum member. ``model_id`` is the actual string sent to the provider API
    and is always present, which keeps the config flexible for provider-specific
    or preview model IDs that are not yet in the enum catalog.
    """

    provider: LLMProvider
    model_id: str
    display_name: str
    model: SupportedModel | None = None
    default_temperature: float = 0.3
    default_top_p: float | None = None
    supports_json_mode: bool = True
    requires_temperature_one: bool = False
    supports_temperature: bool = True
    extra_params: dict[str, Any] = field(default_factory=dict)

    def get_generation_kwargs(self) -> dict[str, Any]:
        """Return the extra kwargs to pass to the chat completion call."""
        kwargs: dict[str, Any] = {}
        if self.supports_temperature:
            kwargs["temperature"] = (
                1.0 if self.requires_temperature_one else self.default_temperature
            )
        if self.default_top_p is not None:
            kwargs["top_p"] = self.default_top_p
        if self.extra_params:
            kwargs.update(self.extra_params)
        return kwargs


# Built-in catalog is intentionally empty. All provider models are loaded from
# the external catalog file (models.yaml) so they can be updated without code
# changes or environment variables.
SUPPORTED_MODELS: list[LLMModelConfig] = []

_MODEL_CONFIG_BY_KEY: dict[tuple[str, str], LLMModelConfig] = {
    (cfg.provider.value, cfg.model_id): cfg for cfg in SUPPORTED_MODELS
}

MODEL_IDS_BY_PROVIDER: dict[str, list[str]] = {}
for _model in SUPPORTED_MODELS:
    MODEL_IDS_BY_PROVIDER.setdefault(_model.provider.value, []).append(_model.model_id)


def _normalise_model_dict(raw: dict[str, Any]) -> dict[str, Any]:
    """Coerce a raw model entry from YAML into the dataclass fields."""
    provider = raw.get("provider")
    model_id = raw.get("model_id")
    if not provider or not model_id:
        raise ValueError(f"Model entry must have 'provider' and 'model_id': {raw}")

    # Resolve optional enum member for known model IDs.
    model: SupportedModel | None = None
    try:
        if provider == LLMProvider.OPENAI.value:
            model = OpenAIModel(model_id)
        elif provider == LLMProvider.GEMINI.value:
            model = GeminiModel(model_id)
    except ValueError:
        model = None

    return {
        "provider": LLMProvider(provider),
        "model_id": model_id,
        "display_name": raw.get("display_name", model_id),
        "model": model,
        "default_temperature": raw.get("default_temperature", 0.3),
        "default_top_p": raw.get("default_top_p"),
        "supports_json_mode": raw.get("supports_json_mode", True),
        "requires_temperature_one": raw.get("requires_temperature_one", False),
        "supports_temperature": raw.get("supports_temperature", True),
        "extra_params": raw.get("extra_params") or {},
    }


def load_models_from_file(path: str | Path) -> list[LLMModelConfig]:
    """Load model definitions from a YAML file.

    The file is expected to contain a top-level ``models`` list. Each item must
    have at least ``provider`` and ``model_id``. All other fields match the
    ``LLMModelConfig`` dataclass and are optional.
    """
    file_path = Path(path)
    if not file_path.exists():
        logger.warning("models_catalog_file_not_found", path=str(file_path))
        return []

    with file_path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    models = data.get("models", [])
    if not isinstance(models, list):
        raise ValueError(f"'models' must be a list in {file_path}")

    configs: list[LLMModelConfig] = []
    for idx, raw in enumerate(models):
        try:
            configs.append(LLMModelConfig(**_normalise_model_dict(raw)))
        except Exception as exc:
            logger.warning(
                "skipping_invalid_model_entry",
                path=str(file_path),
                index=idx,
                error=str(exc),
            )
    return configs


def register_models(configs: list[LLMModelConfig]) -> None:
    """Merge model configs into the in-memory catalog."""
    global _MODEL_CONFIG_BY_KEY, MODEL_IDS_BY_PROVIDER
    for cfg in configs:
        key = (cfg.provider.value, cfg.model_id)
        if key in _MODEL_CONFIG_BY_KEY:
            logger.debug(
                "overwriting_model_config",
                provider=cfg.provider.value,
                model_id=cfg.model_id,
            )
        _MODEL_CONFIG_BY_KEY[key] = cfg
        MODEL_IDS_BY_PROVIDER.setdefault(cfg.provider.value, [])
        if cfg.model_id not in MODEL_IDS_BY_PROVIDER[cfg.provider.value]:
            MODEL_IDS_BY_PROVIDER[cfg.provider.value].append(cfg.model_id)


def initialise_catalog(path: str | Path | None = None) -> None:
    """Load file-based models and merge them with the built-in catalog."""
    if path is None:
        path = "models.yaml"
    file_models = load_models_from_file(path)
    register_models(file_models)


def get_model_config(provider: str, model_id: str) -> LLMModelConfig | None:
    """Return the registered config matching provider + model_id, if any."""
    return _MODEL_CONFIG_BY_KEY.get((provider, model_id))


def get_default_model_config(provider: str) -> LLMModelConfig | None:
    """Return the first registered config for a provider."""
    ids = MODEL_IDS_BY_PROVIDER.get(provider)
    if not ids:
        return None
    return get_model_config(provider, ids[0])


def get_models_for_provider(provider: str) -> list[LLMModelConfig]:
    """Return all registered model configs for a provider."""
    return [cfg for cfg in _MODEL_CONFIG_BY_KEY.values() if cfg.provider.value == provider]


def resolve_model_config(provider: str, model_id: str | None = None) -> LLMModelConfig:
    """Return the config for a provider, preferring an explicit model_id.

    Raises ``ValueError`` when no matching config is registered.
    """
    cfg = get_model_config(provider, model_id) if model_id else None
    if cfg is None and model_id:
        default_cfg = get_default_model_config(provider)
        logger.warning(
            "requested_model_not_in_catalog",
            provider=provider,
            requested_model=model_id,
            fallback_model=default_cfg.model_id if default_cfg else None,
        )
    if cfg is None:
        cfg = get_default_model_config(provider)
    if cfg is None:
        raise ValueError(f"No model configured for provider '{provider}'")
    return cfg
