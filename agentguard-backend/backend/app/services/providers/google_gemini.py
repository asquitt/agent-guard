"""Google Gemini provider adapter."""

from __future__ import annotations

import json

from app.services.providers.base import StreamChunkResult


class GeminiAdapter:
    """Adapter for Google Gemini / Vertex AI API."""

    def build_headers(self, api_key: str) -> dict[str, str]:
        return {
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
        }

    def build_stream_headers(self, api_key: str) -> dict[str, str]:
        return self.build_headers(api_key)

    def inject_stream_options(self, body: dict) -> dict:
        # Gemini includes usage metadata by default
        return body

    def extract_tokens(self, response_data: dict) -> tuple[int | None, int | None]:
        usage = response_data.get("usageMetadata")
        if not usage or not isinstance(usage, dict):
            return None, None
        return usage.get("promptTokenCount"), usage.get("candidatesTokenCount")

    def parse_stream_chunk(self, line: str) -> StreamChunkResult:
        result = StreamChunkResult()
        if not line.startswith("data: "):
            return result
        try:
            chunk_data = json.loads(line[6:])
        except (json.JSONDecodeError, ValueError):
            return result

        # Extract model from modelVersion if present
        result.model = chunk_data.get("modelVersion")

        # Extract content from candidates
        for candidate in chunk_data.get("candidates", []):
            content_obj = candidate.get("content", {})
            for part in content_obj.get("parts", []):
                text = part.get("text")
                if text:
                    result.content = (result.content or "") + text

        # Extract usage from usageMetadata
        usage = chunk_data.get("usageMetadata")
        if usage:
            result.input_tokens = usage.get("promptTokenCount")
            result.output_tokens = usage.get("candidatesTokenCount")

        return result

    def get_default_base_url(self) -> str:
        return "https://generativelanguage.googleapis.com/v1beta"
