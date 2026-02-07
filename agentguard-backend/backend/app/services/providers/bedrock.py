"""AWS Bedrock provider adapter."""

from __future__ import annotations

import json

from app.services.providers.base import StreamChunkResult


class BedrockAdapter:
    """Adapter for AWS Bedrock Runtime API.

    Bedrock supports multiple model families (Anthropic, Meta, Mistral, Amazon).
    Users configure their Bedrock endpoint URL and access credentials via the
    proxy endpoint config. Auth is handled via the API key field (temporary
    session token or access key) passed as a Bearer token.
    """

    def build_headers(self, api_key: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def build_stream_headers(self, api_key: str) -> dict[str, str]:
        return self.build_headers(api_key)

    def inject_stream_options(self, body: dict) -> dict:
        # Bedrock's converse API includes usage by default
        return body

    def extract_tokens(self, response_data: dict) -> tuple[int | None, int | None]:
        # Bedrock converse API format
        usage = response_data.get("usage")
        if not usage or not isinstance(usage, dict):
            return None, None
        return usage.get("inputTokens"), usage.get("outputTokens")

    def parse_stream_chunk(self, line: str) -> StreamChunkResult:
        result = StreamChunkResult()
        if not line.startswith("data: "):
            return result
        try:
            chunk_data = json.loads(line[6:])
        except (json.JSONDecodeError, ValueError):
            return result

        event_type = chunk_data.get("type", "")

        if event_type == "content_block_delta":
            delta = chunk_data.get("delta", {})
            text = delta.get("text")
            if text:
                result.content = text

        elif event_type == "message_start":
            msg = chunk_data.get("message", {})
            result.model = msg.get("model")
            usage = msg.get("usage", {})
            if usage.get("input_tokens"):
                result.input_tokens = usage["input_tokens"]

        elif event_type == "message_delta":
            usage = chunk_data.get("usage", {})
            if usage.get("output_tokens"):
                result.output_tokens = usage["output_tokens"]

        # Also handle Bedrock converse stream format
        if "contentBlockDelta" in chunk_data:
            delta = chunk_data["contentBlockDelta"].get("delta", {})
            text = delta.get("text")
            if text:
                result.content = text

        metadata = chunk_data.get("metadata")
        if metadata:
            usage = metadata.get("usage", {})
            if usage.get("inputTokens"):
                result.input_tokens = usage["inputTokens"]
            if usage.get("outputTokens"):
                result.output_tokens = usage["outputTokens"]

        return result

    def get_default_base_url(self) -> str:
        # Bedrock uses region-specific URLs; users must configure target_url
        return ""
