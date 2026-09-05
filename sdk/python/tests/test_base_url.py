"""Fail-closed deployment origin contract for every credential-bearing SDK path."""

import pytest

from agentguard._base_url import normalize_base_url
from agentguard.integrations.crewai import AgentGuardCrewAIHandler
from agentguard.integrations.langgraph import AgentGuardLangGraphHandler
from agentguard.integrations.llamaindex import AgentGuardCallbackHandler
from agentguard.integrations.otel import AgentGuardSpanExporter


@pytest.mark.parametrize(
    "value",
    [
        "",
        "localhost:8001",
        "/relative",
        "ftp://guard.example.test",
        "http://guard.example.test",
        "http://192.168.1.10:8001",
        "http://10.0.0.5:8001",
        "https://user:password@guard.example.test",
        "https://guard.example.test/api/v1",
        "https://guard.example.test?target=other",
        "https://guard.example.test/#fragment",
    ],
)
def test_normalize_base_url_rejects_non_http_origins(value):
    with pytest.raises(ValueError):
        normalize_base_url(value)


def test_normalize_base_url_strips_trailing_slashes():
    assert normalize_base_url("https://guard.example.test///") == (
        "https://guard.example.test"
    )


@pytest.mark.parametrize(
    "value",
    ["http://localhost:8001", "http://127.0.0.1:8001", "http://[::1]:8001"],
)
def test_normalize_base_url_allows_plaintext_only_on_loopback(value):
    assert normalize_base_url(value) == value


@pytest.mark.parametrize(
    "integration",
    [
        AgentGuardCrewAIHandler,
        AgentGuardLangGraphHandler,
        AgentGuardCallbackHandler,
        AgentGuardSpanExporter,
    ],
)
def test_integrations_require_deployment_base_url(integration):
    with pytest.raises(TypeError):
        integration(api_key="ag_test_key")
