"""Wrap OpenAI and Anthropic clients to route through AgentGuard proxy."""

from __future__ import annotations

from typing import Any

from agentguard._base_url import normalize_base_url


def _build_headers(
    api_key: str,
    endpoint_id: str | None,
    metadata: dict[str, str] | None,
) -> dict[str, str]:
    """Build AgentGuard auth and metadata headers for a provider client."""
    headers = {"Authorization": f"Bearer {api_key}"}
    if endpoint_id:
        headers["X-AgentGuard-Endpoint-Id"] = endpoint_id
    if metadata:
        for key, value in metadata.items():
            headers[f"X-AgentGuard-{key}"] = value
    return headers


def _configure_client(
    client: Any,
    *,
    api_key: str,
    proxy_url: str,
    endpoint_id: str | None,
    metadata: dict[str, str] | None,
) -> Any:
    """Return an official provider-client clone with supported request options."""
    with_options = getattr(client, "with_options", None)
    if not callable(with_options):
        raise TypeError(
            "AgentGuard wrappers require an official OpenAI or Anthropic "
            "client with with_options()"
        )
    return with_options(
        api_key=api_key,
        base_url=proxy_url,
        default_headers=_build_headers(api_key, endpoint_id, metadata),
    )


def wrap_openai(
    client: Any,
    api_key: str,
    base_url: str,
    endpoint_id: str | None = None,
    metadata: dict[str, str] | None = None,
) -> Any:
    """Wrap an OpenAI client to route through AgentGuard.

    Usage::

        import openai
        import agentguard

        agentguard_key = "ag_live_..."
        client = openai.OpenAI(api_key=agentguard_key)
        client = agentguard.wrap_openai(
            client,
            api_key=agentguard_key,
            base_url="http://localhost:8001",
            metadata={"user_id": "u_123", "agent_name": "support-bot"},
        )

    Args:
        client: An ``openai.OpenAI`` or ``openai.AsyncOpenAI`` instance.
        api_key: Your AgentGuard API key (``ag_live_...``).
        base_url: Base URL of the AgentGuard deployment, such as
            ``http://localhost:8001``. The wrapper appends the tracked proxy
            route.
        endpoint_id: UUID of a specific proxy endpoint configuration.
        metadata: Extra key-value pairs sent as ``X-AgentGuard-*`` headers
            (e.g. ``user_id``, ``session_id``, ``agent_name``).

    Returns:
        A configured clone of the provider client. The input client is unchanged.
    """
    proxy_url = f"{normalize_base_url(base_url)}/api/v1/proxy/v1"
    return _configure_client(
        client,
        api_key=api_key,
        proxy_url=proxy_url,
        endpoint_id=endpoint_id,
        metadata=metadata,
    )


def wrap_anthropic(
    client: Any,
    api_key: str,
    base_url: str,
    endpoint_id: str | None = None,
    metadata: dict[str, str] | None = None,
) -> Any:
    """Wrap an Anthropic client to route through AgentGuard.

    Usage::

        import anthropic
        import agentguard

        agentguard_key = "ag_live_..."
        client = anthropic.Anthropic(api_key=agentguard_key)
        client = agentguard.wrap_anthropic(
            client,
            api_key=agentguard_key,
            base_url="http://localhost:8001",
            metadata={"session_id": "sess_456"},
        )

    Args:
        client: An ``anthropic.Anthropic`` or ``anthropic.AsyncAnthropic`` instance.
        api_key: Your AgentGuard API key (``ag_live_...``).
        base_url: Base URL of the AgentGuard deployment, such as
            ``http://localhost:8001``. The Anthropic SDK appends
            ``/v1/messages`` to the proxy base.
        endpoint_id: UUID of a specific proxy endpoint configuration.
        metadata: Extra key-value pairs sent as ``X-AgentGuard-*`` headers.

    Returns:
        A configured clone of the provider client. The input client is unchanged.
    """
    proxy_url = f"{normalize_base_url(base_url)}/api/v1/proxy"
    return _configure_client(
        client,
        api_key=api_key,
        proxy_url=proxy_url,
        endpoint_id=endpoint_id,
        metadata=metadata,
    )
