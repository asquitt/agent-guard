"""AgentGuard Python SDK."""

from agentguard.async_client import AsyncAgentGuardClient
from agentguard.client import AgentGuardClient
from agentguard.exceptions import (
    AgentGuardError,
    AuthenticationError,
    CircuitOpenError,
    DetectionBlockedError,
    RateLimitError,
    ValidationError,
)
from agentguard.types import Detector, Incident, IncidentList, ProxyResponse
from agentguard.wrap import wrap_anthropic, wrap_openai

__all__ = [
    "AgentGuardClient",
    "AsyncAgentGuardClient",
    "wrap_openai",
    "wrap_anthropic",
    # Exceptions
    "AgentGuardError",
    "AuthenticationError",
    "DetectionBlockedError",
    "RateLimitError",
    "CircuitOpenError",
    "ValidationError",
    # Types
    "Incident",
    "IncidentList",
    "ProxyResponse",
    "Detector",
]
__version__ = "0.2.0"
