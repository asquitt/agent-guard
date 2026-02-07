"""Wrap OpenAI and Anthropic clients to route through AgentGuard proxy."""

from __future__ import annotations

from typing import Any


def wrap_openai(
    client: Any,
    api_key: str,
    base_url: str = "https://api.agentguard.app",
    endpoint_id: str | None = None,
) -> Any:
    """Wrap an OpenAI client to route through AgentGuard.

    Usage:
        import openai
        import agentguard

        client = openai.OpenAI(api_key="sk-...")
        client = agentguard.wrap_openai(client, api_key="ag_live_...")

    The client is modified in-place AND returned for convenience.
    """
    proxy_url = f"{base_url.rstrip('/')}/api/v1/proxy/openai/v1"
    client.base_url = proxy_url

    # Inject AgentGuard auth into default headers
    if not hasattr(client, "_custom_headers"):
        client._custom_headers = {}
    client._custom_headers["Authorization"] = f"Bearer {api_key}"
    if endpoint_id:
        client._custom_headers["X-AgentGuard-Endpoint-Id"] = endpoint_id

    return client


def wrap_anthropic(
    client: Any,
    api_key: str,
    base_url: str = "https://api.agentguard.app",
    endpoint_id: str | None = None,
) -> Any:
    """Wrap an Anthropic client to route through AgentGuard.

    Usage:
        import anthropic
        import agentguard

        client = anthropic.Anthropic(api_key="sk-ant-...")
        client = agentguard.wrap_anthropic(client, api_key="ag_live_...")
    """
    proxy_url = f"{base_url.rstrip('/')}/api/v1/proxy/anthropic/v1"
    client._base_url = proxy_url

    if not hasattr(client, "_custom_headers"):
        client._custom_headers = {}
    client._custom_headers["Authorization"] = f"Bearer {api_key}"
    if endpoint_id:
        client._custom_headers["X-AgentGuard-Endpoint-Id"] = endpoint_id

    return client
