"""Tests for agentguard.wrap (wrap_openai / wrap_anthropic)."""

from agentguard.wrap import wrap_anthropic, wrap_openai


class FakeOpenAIClient:
    """Minimal OpenAI client stub."""

    def __init__(self):
        self.base_url = "https://api.openai.com/v1"


class FakeAnthropicClient:
    """Minimal Anthropic client stub."""

    def __init__(self):
        self._base_url = "https://api.anthropic.com/v1"


# ── wrap_openai ──────────────────────────────────────────────────

def test_wrap_openai_sets_base_url():
    client = FakeOpenAIClient()
    result = wrap_openai(client, api_key="ag_live_123")
    assert result is client
    assert client.base_url == "https://api.agentguard.app/api/v1/proxy/openai/v1"


def test_wrap_openai_custom_base_url():
    client = FakeOpenAIClient()
    wrap_openai(client, api_key="k", base_url="https://custom.example.com")
    assert client.base_url == "https://custom.example.com/api/v1/proxy/openai/v1"


def test_wrap_openai_sets_auth_header():
    client = FakeOpenAIClient()
    wrap_openai(client, api_key="ag_live_xyz")
    assert client._custom_headers["Authorization"] == "Bearer ag_live_xyz"


def test_wrap_openai_sets_endpoint_id():
    client = FakeOpenAIClient()
    wrap_openai(client, api_key="k", endpoint_id="ep-abc")
    assert client._custom_headers["X-AgentGuard-Endpoint-Id"] == "ep-abc"


def test_wrap_openai_sets_metadata():
    client = FakeOpenAIClient()
    wrap_openai(client, api_key="k", metadata={"user_id": "u_1", "agent_name": "bot"})
    assert client._custom_headers["X-AgentGuard-user_id"] == "u_1"
    assert client._custom_headers["X-AgentGuard-agent_name"] == "bot"


def test_wrap_openai_no_endpoint_id():
    client = FakeOpenAIClient()
    wrap_openai(client, api_key="k")
    assert "X-AgentGuard-Endpoint-Id" not in client._custom_headers


def test_wrap_openai_trailing_slash_base():
    client = FakeOpenAIClient()
    wrap_openai(client, api_key="k", base_url="https://example.com/")
    assert client.base_url == "https://example.com/api/v1/proxy/openai/v1"


# ── wrap_anthropic ───────────────────────────────────────────────

def test_wrap_anthropic_sets_base_url():
    client = FakeAnthropicClient()
    result = wrap_anthropic(client, api_key="ag_live_456")
    assert result is client
    assert client._base_url == "https://api.agentguard.app/api/v1/proxy/anthropic/v1"


def test_wrap_anthropic_custom_base_url():
    client = FakeAnthropicClient()
    wrap_anthropic(client, api_key="k", base_url="https://custom.example.com")
    assert client._base_url == "https://custom.example.com/api/v1/proxy/anthropic/v1"


def test_wrap_anthropic_sets_auth_header():
    client = FakeAnthropicClient()
    wrap_anthropic(client, api_key="ag_live_abc")
    assert client._custom_headers["Authorization"] == "Bearer ag_live_abc"


def test_wrap_anthropic_sets_endpoint_id():
    client = FakeAnthropicClient()
    wrap_anthropic(client, api_key="k", endpoint_id="ep-def")
    assert client._custom_headers["X-AgentGuard-Endpoint-Id"] == "ep-def"


def test_wrap_anthropic_sets_metadata():
    client = FakeAnthropicClient()
    wrap_anthropic(client, api_key="k", metadata={"session_id": "s_1"})
    assert client._custom_headers["X-AgentGuard-session_id"] == "s_1"


def test_wrap_preserves_existing_custom_headers():
    client = FakeOpenAIClient()
    client._custom_headers = {"X-Existing": "val"}
    wrap_openai(client, api_key="k")
    assert client._custom_headers["X-Existing"] == "val"
    assert client._custom_headers["Authorization"] == "Bearer k"
