"""Provider adapter protocol and shared types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class StreamChunkResult:
    """Parsed result from a single SSE line."""

    content: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    model: str | None = None


@runtime_checkable
class ProviderAdapter(Protocol):
    """Interface that each LLM provider must implement."""

    def build_headers(self, api_key: str) -> dict[str, str]:
        """Build HTTP headers for a non-streaming request."""
        ...

    def build_stream_headers(self, api_key: str) -> dict[str, str]:
        """Build HTTP headers for a streaming request."""
        ...

    def inject_stream_options(self, body: dict) -> dict:
        """Modify request body to enable usage reporting in stream."""
        ...

    def extract_tokens(self, response_data: dict) -> tuple[int | None, int | None]:
        """Extract (input_tokens, output_tokens) from a non-streaming response."""
        ...

    def parse_stream_chunk(self, line: str) -> StreamChunkResult:
        """Parse a single SSE line and extract content/tokens/model."""
        ...

    def get_default_base_url(self) -> str:
        """Return the default upstream base URL for this provider."""
        ...
