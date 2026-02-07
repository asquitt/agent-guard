"""LLM provider adapters — registry and re-exports."""

from app.services.providers.anthropic import AnthropicAdapter
from app.services.providers.azure_openai import AzureOpenAIAdapter
from app.services.providers.base import ProviderAdapter, StreamChunkResult
from app.services.providers.bedrock import BedrockAdapter
from app.services.providers.google_gemini import GeminiAdapter
from app.services.providers.openai import OpenAIAdapter
from app.services.providers.pricing import calculate_cost

__all__ = [
    "ProviderAdapter",
    "StreamChunkResult",
    "get_adapter",
    "calculate_cost",
]

_ADAPTERS: dict[str, ProviderAdapter] = {
    "openai": OpenAIAdapter(),
    "anthropic": AnthropicAdapter(),
    "google_gemini": GeminiAdapter(),
    "azure_openai": AzureOpenAIAdapter(),
    "bedrock": BedrockAdapter(),
}


def get_adapter(provider: str) -> ProviderAdapter:
    """Return the adapter for the given provider name.

    Falls back to OpenAI adapter for unknown providers (e.g. ``custom``),
    since most OpenAI-compatible providers use the same API format.
    """
    return _ADAPTERS.get(provider, _ADAPTERS["openai"])
