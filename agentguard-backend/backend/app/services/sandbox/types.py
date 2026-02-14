"""Shared types for sandbox operations."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CapabilityEvalResult:
    """Result of a capability evaluation."""

    allowed: bool
    matched_capability: str | None = None
    reason: str = ""


@dataclass
class ResourceUsage:
    """Current resource usage snapshot."""

    cpu_seconds: float = 0.0
    memory_peak_mb: float = 0.0
    tokens_used: int = 0
    network_bytes: int = 0


@dataclass
class ResourceLimitViolation:
    """Describes a resource limit breach."""

    resource: str  # cpu, memory, tokens, timeout
    limit: float
    current: float
    message: str = ""


@dataclass
class NetworkPolicyConfig:
    """Parsed network policy for enforcement."""

    allowed_hosts: list[str] = field(default_factory=list)
    allowed_ports: list[int] = field(default_factory=lambda: [443, 80])
    deny_all_egress: bool = True
