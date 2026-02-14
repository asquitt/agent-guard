"""Pre-built sandbox templates for quick-start configurations."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SandboxTemplate:
    """Immutable sandbox template definition."""

    id: str
    name: str
    description: str
    image: str
    capabilities: list[dict[str, str]]
    resource_limits: dict[str, int]
    network_policy: dict[str, object]
    environment: dict[str, str] = field(default_factory=dict)


TEMPLATES: list[SandboxTemplate] = [
    SandboxTemplate(
        id="openai-agent",
        name="OpenAI Agent",
        description="Pre-configured for OpenAI API access with HTTP network capability",
        image="agentguard/sandbox-base:latest",
        capabilities=[
            {"type": "network:http", "target": "*.openai.com"},
            {"type": "api:call", "target": "chat/completions"},
        ],
        resource_limits={
            "cpu_shares": 512,
            "memory_mb": 256,
            "max_tokens": 10000,
            "timeout_seconds": 300,
        },
        network_policy={
            "allowed_hosts": ["api.openai.com"],
            "allowed_ports": [443],
            "deny_all_egress": True,
        },
    ),
    SandboxTemplate(
        id="file-processor",
        name="File Processor",
        description="Read/write file access with high memory for document processing",
        image="agentguard/sandbox-base:latest",
        capabilities=[
            {"type": "file:read", "target": "/data/*"},
            {"type": "file:write", "target": "/output/*"},
        ],
        resource_limits={
            "cpu_shares": 1024,
            "memory_mb": 512,
            "max_tokens": 5000,
            "timeout_seconds": 600,
        },
        network_policy={
            "allowed_hosts": [],
            "allowed_ports": [],
            "deny_all_egress": True,
        },
    ),
    SandboxTemplate(
        id="data-analyst",
        name="Data Analyst",
        description="API access with large token budget for data analysis workflows",
        image="agentguard/sandbox-base:latest",
        capabilities=[
            {"type": "api:call", "target": "*"},
            {"type": "network:http", "target": "*"},
        ],
        resource_limits={
            "cpu_shares": 1024,
            "memory_mb": 512,
            "max_tokens": 50000,
            "timeout_seconds": 900,
        },
        network_policy={
            "allowed_hosts": [],
            "allowed_ports": [443, 80],
            "deny_all_egress": False,
        },
    ),
    SandboxTemplate(
        id="minimal",
        name="Minimal",
        description="Zero capabilities — fully isolated sandbox with default-deny",
        image="agentguard/sandbox-base:latest",
        capabilities=[],
        resource_limits={
            "cpu_shares": 256,
            "memory_mb": 128,
            "max_tokens": 1000,
            "timeout_seconds": 60,
        },
        network_policy={
            "allowed_hosts": [],
            "allowed_ports": [],
            "deny_all_egress": True,
        },
    ),
]

TEMPLATES_BY_ID: dict[str, SandboxTemplate] = {t.id: t for t in TEMPLATES}
