"""Anthropic provider adapter."""

from __future__ import annotations

import json

from app.services.providers.base import StreamChunkResult


class AnthropicAdapter:
    """Adapter for Anthropic Messages API (Claude models)."""

    def build_headers(self, api_key: str) -> dict[str, str]:
        return {
            "x-api-key": api_key,
            "content-type": "application/json",
            "anthropic-version": "2023-06-01",
        }

    def build_stream_headers(self, api_key: str) -> dict[str, str]:
        return self.build_headers(api_key)

    def inject_stream_options(self, body: dict) -> dict:
        # Anthropic includes usage by default in stream events
        return body

    def extract_tokens(self, response_data: dict) -> tuple[int | None, int | None]:
        usage = response_data.get("usage")
        if not usage or not isinstance(usage, dict):
            return None, None
        return usage.get("input_tokens"), usage.get("output_tokens")

    def parse_stream_chunk(self, line: str) -> StreamChunkResult:
        result = StreamChunkResult()
        if not line.startswith("data: "):
            return result
        try:
            chunk_data = json.loads(line[6:])
        except (json.JSONDecodeError, ValueError):
            return result

        event_type = chunk_data.get("type", "")

        if event_type == "message_start":
            msg = chunk_data.get("message", {})
            result.model = msg.get("model")
            usage = msg.get("usage", {})
            if usage.get("input_tokens"):
                result.input_tokens = usage["input_tokens"]

        elif event_type == "content_block_delta":
            delta = chunk_data.get("delta", {})
            if delta.get("type") == "text_delta":
                text = delta.get("text", "")
                if text:
                    result.content = text

        elif event_type == "message_delta":
            usage = chunk_data.get("usage", {})
            if usage.get("output_tokens"):
                result.output_tokens = usage["output_tokens"]

        return result

    def get_default_base_url(self) -> str:
        return "https://api.anthropic.com/v1"
