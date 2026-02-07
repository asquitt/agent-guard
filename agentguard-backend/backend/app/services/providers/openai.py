"""OpenAI provider adapter."""

from __future__ import annotations

import json

from app.services.providers.base import StreamChunkResult


class OpenAIAdapter:
    """Adapter for OpenAI-compatible APIs (GPT-4, GPT-3.5, etc.)."""

    def build_headers(self, api_key: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def build_stream_headers(self, api_key: str) -> dict[str, str]:
        return self.build_headers(api_key)

    def inject_stream_options(self, body: dict) -> dict:
        body.setdefault("stream_options", {})["include_usage"] = True
        return body

    def extract_tokens(self, response_data: dict) -> tuple[int | None, int | None]:
        usage = response_data.get("usage")
        if not usage or not isinstance(usage, dict):
            return None, None
        return usage.get("prompt_tokens"), usage.get("completion_tokens")

    def parse_stream_chunk(self, line: str) -> StreamChunkResult:
        result = StreamChunkResult()
        if not line.startswith("data: ") or line == "data: [DONE]":
            return result
        try:
            chunk_data = json.loads(line[6:])
        except (json.JSONDecodeError, ValueError):
            return result

        result.model = chunk_data.get("model")
        for choice in chunk_data.get("choices", []):
            delta = choice.get("delta", {})
            content = delta.get("content")
            if content:
                result.content = (result.content or "") + content

        usage = chunk_data.get("usage")
        if usage:
            result.input_tokens = usage.get("prompt_tokens")
            result.output_tokens = usage.get("completion_tokens")

        return result

    def get_default_base_url(self) -> str:
        return "https://api.openai.com/v1"
