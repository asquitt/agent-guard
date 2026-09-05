"""Tests for provider-SDK request configuration."""

from __future__ import annotations

from typing import Any

import pytest

from agentguard.wrap import wrap_anthropic, wrap_openai

DEPLOYMENT_BASE_URL = "https://guard.example.test"
AGENTGUARD_KEY = "ag_test_key"
PROVIDER_KEY = "provider-secret-must-not-leave-client"


class RecordingProviderClient:
    """Small double for the official clients' public with_options contract."""

    def __init__(self) -> None:
        self.options: dict[str, Any] | None = None

    def with_options(self, **options: Any) -> RecordingProviderClient:
        clone = RecordingProviderClient()
        clone.options = options
        return clone


def test_wrap_openai_uses_supported_clone_options() -> None:
    original = RecordingProviderClient()
    wrapped = wrap_openai(
        original,
        api_key=AGENTGUARD_KEY,
        base_url=f"{DEPLOYMENT_BASE_URL}/",
        endpoint_id="endpoint-id",
        metadata={"session": "session-id"},
    )

    assert wrapped is not original
    assert original.options is None
    assert wrapped.options == {
        "api_key": AGENTGUARD_KEY,
        "base_url": f"{DEPLOYMENT_BASE_URL}/api/v1/proxy/v1",
        "default_headers": {
            "Authorization": f"Bearer {AGENTGUARD_KEY}",
            "X-AgentGuard-Endpoint-Id": "endpoint-id",
            "X-AgentGuard-session": "session-id",
        },
    }


def test_wrap_anthropic_uses_supported_clone_options() -> None:
    original = RecordingProviderClient()
    wrapped = wrap_anthropic(
        original,
        api_key=AGENTGUARD_KEY,
        base_url=DEPLOYMENT_BASE_URL,
    )

    assert wrapped.options == {
        "api_key": AGENTGUARD_KEY,
        "base_url": f"{DEPLOYMENT_BASE_URL}/api/v1/proxy",
        "default_headers": {
            "Authorization": f"Bearer {AGENTGUARD_KEY}",
        },
    }


def test_wrappers_require_an_explicit_deployment_origin() -> None:
    with pytest.raises(TypeError):
        wrap_openai(  # pyright: ignore[reportCallIssue]
            RecordingProviderClient(), api_key=AGENTGUARD_KEY
        )
    with pytest.raises(ValueError, match="deployment origin"):
        wrap_anthropic(
            RecordingProviderClient(),
            api_key=AGENTGUARD_KEY,
            base_url="https://guard.example.test/untrusted-path",
        )


def test_wrappers_reject_lookalike_clients() -> None:
    with pytest.raises(TypeError, match="with_options"):
        wrap_openai(
            object(),
            api_key=AGENTGUARD_KEY,
            base_url=DEPLOYMENT_BASE_URL,
        )


def test_real_openai_client_sends_tracked_route_and_headers() -> None:
    httpx = pytest.importorskip("httpx")
    openai = pytest.importorskip("openai")
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "created": 0,
                "model": "gpt-4o-mini",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "ok"},
                        "finish_reason": "stop",
                    }
                ],
            },
        )

    original = openai.OpenAI(
        api_key=PROVIDER_KEY,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    wrapped = wrap_openai(
        original,
        api_key=AGENTGUARD_KEY,
        base_url=DEPLOYMENT_BASE_URL,
        endpoint_id="endpoint-id",
        metadata={"session": "session-id"},
    )
    wrapped.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "hello"}],
    )

    request = requests[0]
    assert str(request.url) == (
        f"{DEPLOYMENT_BASE_URL}/api/v1/proxy/v1/chat/completions"
    )
    assert request.headers["Authorization"] == f"Bearer {AGENTGUARD_KEY}"
    assert request.headers["X-AgentGuard-Endpoint-Id"] == "endpoint-id"
    assert request.headers["X-AgentGuard-session"] == "session-id"
    assert PROVIDER_KEY not in request.headers.values()


def test_real_anthropic_client_sends_tracked_route_and_headers() -> None:
    httpx = pytest.importorskip("httpx")
    anthropic = pytest.importorskip("anthropic")
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "model": "claude-test-model",
                "content": [{"type": "text", "text": "ok"}],
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 1, "output_tokens": 1},
            },
        )

    original = anthropic.Anthropic(
        api_key=PROVIDER_KEY,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    wrapped = wrap_anthropic(
        original,
        api_key=AGENTGUARD_KEY,
        base_url=DEPLOYMENT_BASE_URL,
        endpoint_id="endpoint-id",
        metadata={"session": "session-id"},
    )
    wrapped.messages.create(
        model="claude-test-model",
        max_tokens=1,
        messages=[{"role": "user", "content": "hello"}],
    )

    request = requests[0]
    assert str(request.url) == f"{DEPLOYMENT_BASE_URL}/api/v1/proxy/v1/messages"
    assert request.headers["Authorization"] == f"Bearer {AGENTGUARD_KEY}"
    assert request.headers["X-AgentGuard-Endpoint-Id"] == "endpoint-id"
    assert request.headers["X-AgentGuard-session"] == "session-id"
    assert PROVIDER_KEY not in request.headers.values()
