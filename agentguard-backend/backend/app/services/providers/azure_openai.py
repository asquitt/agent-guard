"""Azure OpenAI provider adapter."""

from __future__ import annotations

from app.services.providers.openai import OpenAIAdapter


class AzureOpenAIAdapter(OpenAIAdapter):
    """Adapter for Azure OpenAI Service.

    Same SSE format and token extraction as OpenAI, but uses
    ``api-key`` header instead of ``Authorization: Bearer``.
    """

    def build_headers(self, api_key: str) -> dict[str, str]:
        return {
            "api-key": api_key,
            "Content-Type": "application/json",
        }

    def build_stream_headers(self, api_key: str) -> dict[str, str]:
        return self.build_headers(api_key)

    def get_default_base_url(self) -> str:
        # Azure uses custom deployment URLs; users must configure target_url
        return ""
