from pydantic import BaseModel


class LLMModelInfo(BaseModel):
    """Public information about a single LLM model."""

    id: str
    display_name: str
    default_temperature: float
    supports_json_mode: bool


class LLMProviderInfo(BaseModel):
    """Public information about an LLM provider and its available models."""

    id: str
    display_name: str
    models: list[LLMModelInfo]


class LLMProvidersResponse(BaseModel):
    """Response payload for the configured LLM providers endpoint."""

    providers: list[LLMProviderInfo]
