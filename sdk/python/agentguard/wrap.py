"""Wrap OpenAI and Anthropic clients to route through AgentGuard proxy."""

from __future__ import annotations

from typing import Any


def _apply_headers(
    client: Any,
    api_key: str,
    base_url: str,
    endpoint_id: str | None,
    metadata: dict[str, str] | None,
    header_attr: str = "_custom_headers",
) -> None:
    """Inject AgentGuard auth and metadata headers into a client."""
    if not hasattr(client, header_attr):
        setattr(client, header_attr, {})
    headers: dict[str, str] = getattr(client, header_attr)
    headers["Authorization"] = f"Bearer {api_key}"
    if endpoint_id:
        headers["X-AgentGuard-Endpoint-Id"] = endpoint_id
    if metadata:
        for key, value in metadata.items():
            headers[f"X-AgentGuard-{key}"] = value


def wrap_openai(
    client: Any,
    api_key: str,
    base_url: str = "https://api.agentguard.app",
    endpoint_id: str | None = None,
    metadata: dict[str, str] | None = None,
) -> Any:
    """Wrap an OpenAI client to route through AgentGuard.

    Usage::

        import openai
        import agentguard

        client = openai.OpenAI(api_key="sk-...")
        client = agentguard.wrap_openai(
            client,
            api_key="ag_live_...",
            metadata={"user_id": "u_123", "agent_name": "support-bot"},
        )

    Args:
        client: An ``openai.OpenAI`` or ``openai.AsyncOpenAI`` instance.
        api_key: Your AgentGuard API key (``ag_live_...``).
        base_url: Custom AgentGuard proxy URL.
        endpoint_id: UUID of a specific proxy endpoint configuration.
        metadata: Extra key-value pairs sent as ``X-AgentGuard-*`` headers
            (e.g. ``user_id``, ``session_id``, ``agent_name``).

    Returns:
        The wrapped client (modified in-place and returned for convenience).
    """
    proxy_url = f"{base_url.rstrip('/')}/api/v1/proxy/openai/v1"
    client.base_url = proxy_url
    _apply_headers(client, api_key, base_url, endpoint_id, metadata)
    return client


def wrap_anthropic(
    client: Any,
    api_key: str,
    base_url: str = "https://api.agentguard.app",
    endpoint_id: str | None = None,
    metadata: dict[str, str] | None = None,
) -> Any:
    """Wrap an Anthropic client to route through AgentGuard.

    Usage::

        import anthropic
        import agentguard

        client = anthropic.Anthropic(api_key="sk-ant-...")
        client = agentguard.wrap_anthropic(
            client,
            api_key="ag_live_...",
            metadata={"session_id": "sess_456"},
        )

    Args:
        client: An ``anthropic.Anthropic`` or ``anthropic.AsyncAnthropic`` instance.
        api_key: Your AgentGuard API key (``ag_live_...``).
        base_url: Custom AgentGuard proxy URL.
        endpoint_id: UUID of a specific proxy endpoint configuration.
        metadata: Extra key-value pairs sent as ``X-AgentGuard-*`` headers.

    Returns:
        The wrapped client.
    """
    proxy_url = f"{base_url.rstrip('/')}/api/v1/proxy/anthropic/v1"
    client._base_url = proxy_url
    _apply_headers(client, api_key, base_url, endpoint_id, metadata)
    return client
